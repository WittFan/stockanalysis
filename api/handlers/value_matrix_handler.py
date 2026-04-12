"""
价值坐标系 Handler

直接调用 Tushare fina_indicator 接口，不依赖本地数据库。

路由（Flask API）：
  GET  /api/value/data?year=2023&metric=gross  → JSON {stocks, count}
  GET  /api/value/data?year=5y&metric=gross    → JSON {stocks, count, year_range}
  POST /api/value/forecast                     → JSON {stocks}

近5年（year=5y）计算规则：
  - 年份范围：动态，取当前年份往前5个已完成年报年度
  - 销售毛利率/净利率（x）：近5年 算术平均值
  - 营业收入同比增长率（y）：近5年 累积平均值（几何平均，即 CAGR）
    CAGR = ((1+g1)*(1+g2)*...*(1+gn))^(1/n) - 1
"""
import datetime
import json
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout

import pandas as pd
from loguru import logger

from api.cache import value_cache
from api.stockpool import load_stockpool


# ── 常量 ──────────────────────────────────────────────────────────────────────

AVAILABLE_YEARS  = list(range(datetime.date.today().year - 1, datetime.date.today().year - 6, -1))
DEFAULT_YEAR     = 2024
MULTI_YEAR_KEY   = '5y'              # 近5年模式的参数值
MULTI_YEAR_COUNT = 5                 # 近N年
TUSHARE_FIELDS   = 'ts_code,ann_date,end_date,grossprofit_margin,netprofit_margin,or_yoy'


def get_recent_years(n: int = MULTI_YEAR_COUNT) -> list:
    """返回最近 n 个已完成年报年度（动态，按当前日期推算）。
    例如：今天 2026-04-10 → 最新完整年报为 2025 → 返回 [2021,2022,2023,2024,2025]
    """
    latest = datetime.date.today().year - 1
    return list(range(latest - n + 1, latest + 1))


# ── 数据获取 ──────────────────────────────────────────────────────────────────

def fetch_fina_data(symbols: list, year: int) -> pd.DataFrame:
    """
    从 Tushare 并发获取年报财务指标，结果按年缓存。
    最多 5 个并发线程，每个调用最长等待 15s，避免单只挂死。
    """
    raw_cache_key = f'raw_{year}'
    if value_cache.has(raw_cache_key):
        return value_cache.get(raw_cache_key)

    from config import pro

    period = f'{year}1231'
    logger.info(f"开始拉取 {year} 年报财务指标，共 {len(symbols)} 只股票（并发5线程）")

    def _fetch_one(ts_code: str):
        try:
            df = pro.fina_indicator(ts_code=ts_code, period=period, fields=TUSHARE_FIELDS)
            if df is not None and not df.empty:
                return df.sort_values('ann_date', ascending=False).iloc[0].to_dict()
        except Exception as e:
            logger.warning(f"获取 {ts_code} {year}年财务数据失败: {e}")
        return None

    rows = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_fetch_one, code): code for code in symbols}
        for future in as_completed(futures, timeout=300):
            try:
                row = future.result(timeout=15)
                if row is not None:
                    rows.append(row)
            except FuturesTimeout:
                logger.warning(f"获取 {futures[future]} 超时，跳过")
            except Exception as e:
                logger.warning(f"获取 {futures[future]} 异常: {e}")

    if rows:
        result = pd.DataFrame(rows)[['ts_code', 'ann_date', 'end_date',
                                      'grossprofit_margin', 'netprofit_margin', 'or_yoy']]
    else:
        result = pd.DataFrame(columns=['ts_code', 'ann_date', 'end_date',
                                        'grossprofit_margin', 'netprofit_margin', 'or_yoy'])

    logger.info(f"{year} 年报数据拉取完成：{len(result)} 条有效记录")
    value_cache.set(raw_cache_key, result, ttl=3600)  # 财务数据缓存1小时
    return result


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

        # 逐年拉取（复用单年缓存，无网络调用时 O(1)）
        year_dfs: dict = {}
        for y in years:
            year_dfs[y] = fetch_fina_data(self.symbols, y)

        # 为方便 O(1) 查找，将每年 DataFrame 转成 {ts_code: row_dict}
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
            # 负乘积时保留符号再开方（奇数次根对负数合法）
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
                'year_range': [years[0], years[-1]],   # [2021, 2025]
            }
            value_cache.set(chart_cache_key, result, ttl=3600)
            logger.info(f"handle_data_api：近{MULTI_YEAR_COUNT}年({years[0]}-{years[-1]}) {metric}，有效数据 {len(stocks)} 条")
            return 200, result

        # ── 单年模式 ────────────────────────────────────────────────────
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

        # 基本校验：x/y 必须存在且可转为整数
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
