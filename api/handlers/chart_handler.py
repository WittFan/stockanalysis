"""
股票池趋势图 Handler

路由（Flask API）：
  GET /api/chart?period={1|2|3}    → JSON {dates, series, count}
  GET /api/industry?period={1|2|3} → JSON {dates, groups, total}
"""
import colorsys
from datetime import date, timedelta

import pandas as pd
from loguru import logger
from sqlalchemy import text

from api.cache import chart_cache, industry_cache
from api.stockpool import load_stockpool  # noqa: F401（重新导出，供历史兼容）


# ── 颜色生成 ──────────────────────────────────────────────────────────────────

_PALETTE_20 = [
    '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c',
    '#98df8a', '#d62728', '#ff9896', '#9467bd', '#c5b0d5',
    '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f',
    '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5',
]


def _make_colors(n: int) -> list:
    """生成 n 个十六进制颜色值；n≤20 使用预设调色板，超出则用 HLS 均匀分布。"""
    if n <= 20:
        return _PALETTE_20[:n]
    colors = []
    for i in range(n):
        h = i / n
        r, g, b = colorsys.hls_to_rgb(h, 0.5, 0.7)
        colors.append('#{:02x}{:02x}{:02x}'.format(int(r * 255), int(g * 255), int(b * 255)))
    return colors


# ── 数据加载 ──────────────────────────────────────────────────────────────────

def load_and_normalize(symbols: list, period_years: int) -> pd.DataFrame:
    """使用 Duckdbloader 加载后复权收盘价并归一化（起始日 = 1.0）。"""
    from datafeed.dataloader import Duckdbloader

    end_date   = date.today().strftime('%Y%m%d')
    start_date = (date.today() - timedelta(days=period_years * 365 + 10)).strftime('%Y%m%d')

    logger.info(f"查询数据：{start_date} ~ {end_date}，股票数：{len(symbols)}")

    loader = Duckdbloader(
        path='',
        symbols=symbols,
        columns=['close'],
        start_date=start_date,
        end_date=end_date,
    )
    df = loader.load()

    if df.empty:
        logger.warning("未查询到任何数据，请检查数据库和股票代码格式")
        return pd.DataFrame()

    df_pivot    = df.pivot_table(index=df.index, columns='symbol', values='close')
    first_valid = df_pivot.apply(lambda col: col.dropna().iloc[0] if not col.dropna().empty else 1.0)
    df_norm     = df_pivot.div(first_valid)

    logger.info(f"数据加载完成：{len(df_norm)} 个交易日，{len(df_norm.columns)} 只有效股票")
    return df_norm


def load_industry_map(symbols: list) -> dict:
    """查询申万一级行业映射，返回 {ts_code: industry_name}。"""
    from orm_models.api import session as db_session

    placeholders = ', '.join([f"'{s}'" for s in symbols])
    sql = f"""
        SELECT m.con_code, c.industry_name
        FROM index_member m
        JOIN index_classify c ON m.index_code = c.index_code
        WHERE m.con_code IN ({placeholders})
          AND m.is_new  = 'Y'
          AND c.level   = 'L1'
    """
    df = pd.read_sql(text(sql), db_session.bind)
    df = df.drop_duplicates(subset='con_code')
    result = dict(zip(df['con_code'], df['industry_name']))
    logger.info(f"行业映射：{len(result)}/{len(symbols)} 只股票匹配到申万L1行业")
    return result


# ── 纯数据构建 ────────────────────────────────────────────────────────────────

def build_chart_data(df_norm: pd.DataFrame, code_to_name: dict, period_years: int) -> dict:
    """
    构建总览折线图数据，返回前端 ECharts 所需的纯 JSON dict：
    {
      'dates':  ['2022-01-04', ...],   # 日期字符串列表
      'series': [
        {'sym': '600519.SH', 'name': '贵州茅台', 'color': '#1f77b4',
         'values': [1.0, 1.02, ...]},  # NaN 替换为 None，保留4位小数
        ...
      ],
      'count': 198
    }
    """
    n = len(df_norm.columns)
    if n == 0:
        return {'dates': [], 'series': [], 'count': 0}

    # 日期轴：格式化为 YYYY-MM-DD 字符串
    dates = [d.strftime('%Y-%m-%d') for d in df_norm.index]

    colors  = _make_colors(n)
    series  = []
    for i, sym in enumerate(df_norm.columns):
        name   = code_to_name.get(sym, sym)
        values = [
            round(v, 4) if pd.notna(v) else None
            for v in df_norm[sym]
        ]
        series.append({
            'sym':    sym,
            'name':   name,
            'color':  colors[i],
            'values': values,
        })

    logger.info(f"build_chart_data 完成：{len(dates)} 个交易日，{n} 只股票")
    return {'dates': dates, 'series': series, 'count': n}


def build_industry_data(df_norm: pd.DataFrame, code_to_name: dict,
                        ind_map: dict, period: int) -> dict:
    """
    按申万L1行业分组，返回前端 ECharts 所需的纯 JSON dict：
    {
      'dates':  ['2022-01-04', ...],   # 共享日期轴
      'groups': [
        {'name': '食品饮料', 'count': 5,
         'series': [{'sym':..., 'name':..., 'color':..., 'values':[...]}, ...]},
        ...
      ],
      'total': 198
    }
    """
    # 按行业分组
    groups: dict = {}
    for sym in df_norm.columns:
        groups.setdefault(ind_map.get(sym, '未分类'), []).append(sym)

    sorted_groups = sorted(groups.items(), key=lambda x: -len(x[1]))
    logger.info(f"行业分组完成：{len(sorted_groups)} 个行业")

    # 共享日期轴
    dates = [d.strftime('%Y-%m-%d') for d in df_norm.index]

    result_groups = []
    for ind_name, syms in sorted_groups:
        n      = len(syms)
        colors = _make_colors(n)
        series = []
        for i, sym in enumerate(syms):
            name   = code_to_name.get(sym, sym)
            values = [
                round(v, 4) if pd.notna(v) else None
                for v in df_norm[sym]
            ]
            series.append({
                'sym':    sym,
                'name':   name,
                'color':  colors[i],
                'values': values,
            })
        result_groups.append({'name': ind_name, 'count': n, 'series': series})

    return {
        'dates':  dates,
        'groups': result_groups,
        'total':  len(df_norm.columns),
    }


# ── Handler 类 ────────────────────────────────────────────────────────────────

class ChartHandler:
    """处理 /api/chart 和 /api/industry 请求，返回纯 JSON 数据（供前端 ECharts 使用）。"""

    def __init__(self):
        self.code_to_name: dict = {}
        self.symbols: list      = []

    def init(self, xlsx_path: str):
        self.code_to_name = load_stockpool(xlsx_path)
        self.symbols      = list(self.code_to_name.keys())

    def handle_chart(self, period: int) -> dict:
        """返回 {dates, series, count}"""
        if not chart_cache.has(period):
            df_norm = load_and_normalize(self.symbols, period)
            data    = build_chart_data(df_norm, self.code_to_name, period)
            chart_cache.set(period, data)

        return chart_cache.get(period)

    def handle_industry(self, period: int) -> dict:
        """返回 {dates, groups, total}"""
        if not industry_cache.has(period):
            df_norm = load_and_normalize(self.symbols, period)
            ind_map = load_industry_map(self.symbols)
            data    = build_industry_data(df_norm, self.code_to_name, ind_map, period)
            industry_cache.set(period, data)

        return industry_cache.get(period)
