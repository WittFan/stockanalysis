"""
价值坐标系 Handler

数据来源：本地 PostgreSQL fina_indicator 表（年报/季报数据）。
每只股票取该 end_date 下 ann_date 最新的一条记录（DISTINCT ON）。

路由（Flask API）：
  GET  /api/value/data?year=2023&metric=gross  → JSON {stocks, count}
  GET  /api/value/data?year=5y&metric=gross    → JSON {stocks, count, year_range}
  POST /api/value/forecast                     → JSON {stocks}

近5年（year=5y）最新一年的数据获取规则（季度感知）：
  - 一季度（1-3月）：用去年三季报（end_date=YYYY0930）代替去年全年
  - 二季度（4-6月）：优先用去年年报（end_date=YYYY1231），无年报数据则用三季报
  - 三、四季度（7-12月）：使用去年年报（end_date=YYYY1231）

近5年聚合计算规则：
  - 销售毛利率/净利率（x）：近5年 算术平均值
  - 营业收入同比增长率（y）：近5年 累积平均值（几何平均，即 CAGR）
    CAGR = ((1+g1)*(1+g2)*...*(1+gn))^(1/n) - 1
"""
import datetime
import json

import pandas as pd
from loguru import logger
from sqlalchemy import text

from api.cache import value_cache
from api.stockpool import load_stockpool
from orm_models.api import engine


# ── 常量 ──────────────────────────────────────────────────────────────────────

AVAILABLE_YEARS  = list(range(datetime.date.today().year - 1, datetime.date.today().year - 6, -1))
DEFAULT_YEAR     = AVAILABLE_YEARS[0]
MULTI_YEAR_KEY   = '5y'              # 近5年模式的参数值
MULTI_YEAR_COUNT = 5                 # 近N年
DB_FIELDS        = 'ts_code, ann_date, end_date, grossprofit_margin, netprofit_margin, or_yoy'


def get_current_quarter() -> int:
    """返回当前季度（1/2/3/4）。"""
    month = datetime.date.today().month
    return (month - 1) // 3 + 1


def get_recent_years(n: int = MULTI_YEAR_COUNT) -> list:
    """返回最近 n 个已完成年报年度（动态，按当前日期推算）。
    例如：今天 2026-04-10 → 最新完整年报为 2025 → 返回 [2021,2022,2023,2024,2025]
    """
    latest = datetime.date.today().year - 1
    return list(range(latest - n + 1, latest + 1))


# ── 数据获取（从 PostgreSQL 查询）────────────────────────────────────────────

def fetch_fina_data(symbols: list, year: int, end_date: str = None) -> pd.DataFrame:
    """
    从本地 PostgreSQL fina_indicator 表查询财务指标，结果按 end_date 缓存。

    策略：每只股票取该 end_date 下 ann_date 最新的一条（DISTINCT ON）。
    end_date 不传时默认使用 '{year}1231'（年报）。
    支持传入季报 end_date，如 '20250930'（三季报）。
    """
    end_date_str  = end_date if end_date else f'{year}1231'
    raw_cache_key = f'raw_{end_date_str}'
    if value_cache.has(raw_cache_key):
        return value_cache.get(raw_cache_key)

    # 若有股票池过滤，用 IN 子句；否则查全部
    if symbols:
        placeholders = ', '.join(f"'{s}'" for s in symbols)
        where_extra  = f"AND ts_code IN ({placeholders})"
    else:
        where_extra = ''

    sql = text(f"""
        SELECT DISTINCT ON (ts_code)
            ts_code, ann_date, end_date,
            grossprofit_margin, netprofit_margin, or_yoy
        FROM fina_indicator
        WHERE end_date = :end_date
        {where_extra}
        ORDER BY ts_code, ann_date DESC
    """)

    try:
        with engine.connect() as con:
            result = pd.read_sql(sql, con, params={'end_date': end_date_str})
    except Exception as e:
        logger.error(f"查询 fina_indicator end_date={end_date_str} 失败: {e}")
        result = pd.DataFrame(columns=['ts_code', 'ann_date', 'end_date',
                                        'grossprofit_margin', 'netprofit_margin', 'or_yoy'])

    logger.info(f"fina_indicator end_date={end_date_str} 查询完成：{len(result)} 条有效记录")
    value_cache.set(raw_cache_key, result, ttl=3600)   # 缓存1小时
    return result


def fetch_latest_year_data(symbols: list, latest_year: int) -> pd.DataFrame:
    """
    按当前季度决定最新年份的数据来源，返回合并后的 DataFrame（每股最多1条）。

    规则：
      一季度（1-3月）：用去年三季报（YYYY0930）代替年报
      二季度（4-6月）：优先年报（YYYY1231），无年报则用三季报（YYYY0930）
      三、四季度（7-12月）：直接用年报（YYYY1231）
    """
    quarter = get_current_quarter()

    if quarter == 1:
        # 一季度：年报尚未披露完，用三季报代替
        df = fetch_fina_data(symbols, latest_year, end_date=f'{latest_year}0930')
        logger.info(f"最新年份 {latest_year}：当前一季度，使用三季报（{latest_year}0930）代替年报")
        return df

    if quarter >= 3:
        # 三、四季度：年报已充分披露
        df = fetch_fina_data(symbols, latest_year)
        logger.info(f"最新年份 {latest_year}：当前{quarter}季度，直接使用年报（{latest_year}1231）")
        return df

    # 二季度：年报优先，缺失股票用三季报补充
    df_annual  = fetch_fina_data(symbols, latest_year)                              # 年报
    df_q3      = fetch_fina_data(symbols, latest_year, end_date=f'{latest_year}0930')  # 三季报

    annual_codes = set(df_annual['ts_code'].tolist()) if not df_annual.empty else set()
    q3_codes     = set(df_q3['ts_code'].tolist())     if not df_q3.empty  else set()
    fallback_codes = q3_codes - annual_codes           # 只有三季报、无年报的股票

    if fallback_codes:
        df_fallback = df_q3[df_q3['ts_code'].isin(fallback_codes)]
        df_merged   = pd.concat([df_annual, df_fallback], ignore_index=True)
        logger.info(
            f"最新年份 {latest_year}：二季度，年报 {len(annual_codes)} 条，"
            f"三季报补充 {len(fallback_codes)} 条"
        )
        return df_merged

    logger.info(f"最新年份 {latest_year}：二季度，年报 {len(annual_codes)} 条，无需三季报补充")
    return df_annual


# ── Handler 类 ────────────────────────────────────────────────────────────────

class ValueMatrixHandler:
    """处理 /api/value/data、/api/value/forecast 请求，返回纯 JSON 数据（供前端 ECharts 使用）。"""

    def __init__(self):
        self.code_to_name: dict = {}
        self.symbols: list = []

    def init(self, xlsx_path: str):
        self.code_to_name = load_stockpool(xlsx_path)
        self.symbols = list(self.code_to_name.keys())

    @staticmethod
    def _parse_params(qs: dict) -> tuple:
        """解析 GET 请求参数，返回 (year, metric)。
        year 可以是 int（单年）或字符串 '5y'（近5年聚合）。
        """
        year_raw = qs.get('year', [str(DEFAULT_YEAR)])[0]
        if year_raw == MULTI_YEAR_KEY:
            year = MULTI_YEAR_KEY
        else:
            try:
                year = int(year_raw)
            except (ValueError, TypeError):
                year = DEFAULT_YEAR
            if year not in AVAILABLE_YEARS:
                year = DEFAULT_YEAR

        metric = qs.get('metric', ['gross'])[0]
        if metric not in ('gross', 'net'):
            metric = 'gross'
        return year, metric

    def _build_multiyear_stocks(self, metric: str) -> tuple:
        """
        近5年聚合计算：
          x（毛利率/净利率）= 近5年 算术平均值
          y（营收增速）     = 近5年 累积平均值（CAGR）
            CAGR = ((1+g1/100)*(1+g2/100)*...*(1+gn/100))^(1/n) - 1，结果乘以100
        只有至少拥有1年有效 x 数据且至少1年有效 y 数据的股票才纳入。
        返回 (stocks_list, years_list)。
        """
        years  = get_recent_years(MULTI_YEAR_COUNT)
        x_col  = 'grossprofit_margin' if metric == 'gross' else 'netprofit_margin'

        # 逐年查询（复用单年缓存）
        # 最新年份使用季度感知逻辑，历史年份直接取年报
        latest_year = years[-1]
        year_dfs: dict = {}
        for y in years:
            if y == latest_year:
                year_dfs[y] = fetch_latest_year_data(self.symbols, y)
            else:
                year_dfs[y] = fetch_fina_data(self.symbols, y)

        # 转成 {ts_code: row_dict} 便于 O(1) 查找
        year_maps: dict = {}
        for y, df in year_dfs.items():
            year_maps[y] = df.set_index('ts_code').to_dict(orient='index') if not df.empty else {}

        stocks = []
        for ts_code in self.symbols:
            x_vals    = []   # 有效毛利率/净利率值列表
            g_factors = []   # 有效增长因子列表（1 + growth_rate/100）

            for y in years:
                row = year_maps[y].get(ts_code)
                if row is None:
                    continue
                xv = row.get(x_col)
                yv = row.get('or_yoy')
                if xv is not None and not pd.isna(xv):
                    x_vals.append(float(xv))
                if yv is not None and not pd.isna(yv):
                    g_factors.append(1.0 + float(yv) / 100.0)

            if not x_vals or not g_factors:
                continue

            # 算术平均值
            x_mean = sum(x_vals) / len(x_vals)

            # 几何平均（CAGR）
            product = 1.0
            for f in g_factors:
                product *= f
            n = len(g_factors)
            if product < 0:
                cagr = -((-product) ** (1.0 / n) + 1.0) * 100.0
            else:
                cagr = (product ** (1.0 / n) - 1.0) * 100.0

            stocks.append({
                'code': ts_code,
                'name': self.code_to_name.get(ts_code, ts_code),
                'x':   int(round(x_mean)),
                'y':   int(round(cagr)),
            })

        return stocks, years

    def handle_data_api(self, qs: dict) -> tuple:
        """
        GET /value/data → (200, {'stocks': [...], 'count': N})
        year=5y 时额外返回 'year_range': [start, end]。

        stocks 格式：[{'code':'600519.SH', 'name':'贵州茅台', 'x':92, 'y':18}, ...]
        x/y 为整数（毛利率/净利率、营收增速），NaN 的记录直接跳过。
        """
        year, metric = self._parse_params(qs)
        chart_cache_key = (year, metric)

        if value_cache.has(chart_cache_key):
            return 200, value_cache.get(chart_cache_key)

        # ── 近5年聚合模式 ──────────────────────────────────────────────
        if year == MULTI_YEAR_KEY:
            stocks, years = self._build_multiyear_stocks(metric)
            result = {
                'stocks':     stocks,
                'count':      len(stocks),
                'year_range': [years[0], years[-1]],
            }
            value_cache.set(chart_cache_key, result, ttl=3600)
            logger.info(f"handle_data_api：近{MULTI_YEAR_COUNT}年({years[0]}-{years[-1]}) {metric}，有效数据 {len(stocks)} 条")
            return 200, result

        # ── 单年模式 ────────────────────────────────────────────────────
        # 最新年份使用季度感知逻辑，与近5年中最新年的数据来源保持一致
        latest_year = AVAILABLE_YEARS[0]
        if year == latest_year:
            raw_df = fetch_latest_year_data(self.symbols, year)
        else:
            raw_df = fetch_fina_data(self.symbols, year)
        x_col  = 'grossprofit_margin' if metric == 'gross' else 'netprofit_margin'

        stocks = []
        for _, row in raw_df.iterrows():
            ts_code = row['ts_code']
            xv = row.get(x_col)
            yv = row.get('or_yoy')
            if pd.isna(xv) or pd.isna(yv):
                continue
            stocks.append({
                'code': ts_code,
                'name': self.code_to_name.get(ts_code, ts_code),
                'x':   int(round(float(xv))),
                'y':   int(round(float(yv))),
            })

        result = {'stocks': stocks, 'count': len(stocks)}
        value_cache.set(chart_cache_key, result, ttl=3600)
        logger.info(f"handle_data_api：{year} 年 {metric}，有效数据 {len(stocks)} 条")
        return 200, result

    def handle_forecast(self, body: bytes) -> tuple:
        """
        POST /value/forecast → (200, {'stocks': [...]})

        前端传入预期数据，原样校验后返回，由前端自行渲染 ECharts 散点图。
        stocks 格式：[{'code':..., 'name':..., 'x':int, 'y':int}, ...]
        """
        try:
            data = json.loads(body.decode('utf-8'))
        except Exception:
            return 400, {'error': '无效的 JSON 数据'}

        metric = data.get('metric', 'gross')
        if metric not in ('gross', 'net'):
            metric = 'gross'

        raw_stocks = data.get('stocks', [])
        if not raw_stocks:
            return 400, {'error': '预期数据为空'}

        stocks = []
        for s in raw_stocks:
            try:
                xv = s.get('x')
                yv = s.get('y')
                if xv is None or yv is None:
                    continue
                stocks.append({
                    'code': str(s['code']),
                    'name': str(s['name']),
                    'x':   int(xv),
                    'y':   int(yv),
                })
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"跳过无效预期数据项：{s}，原因：{e}")

        if not stocks:
            return 400, {'error': '所有预期数据项均无效'}

        logger.info(f"handle_forecast：metric={metric}，有效预期数据 {len(stocks)} 条")
        return 200, {'stocks': stocks}
