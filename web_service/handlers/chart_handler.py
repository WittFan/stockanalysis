"""
股票池趋势图 Handler（迁移自 stock_trend_service.py）

路由：
  GET /chart?period={1|2|3}    → 总览折线图
  GET /industry?period={1|2|3} → 申万L1行业分组视图
"""
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from bokeh.embed import components
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.palettes import Category20, turbo
from bokeh.plotting import figure
from bokeh.resources import CDN
from loguru import logger
from sqlalchemy import text

from web_service.cache import chart_cache, industry_cache
from web_service.ui import NAV_CSS, build_nav


# ── 数据加载 ──────────────────────────────────────────────────────────────────

def load_stockpool(xlsx_path: str) -> dict:
    """读取 stockpool.xlsx，返回去重后的 {股票代码: 标的名称} 字典。"""
    df = pd.read_excel(xlsx_path, sheet_name='出入池时间表A股')
    stocks = (
        df[['标的名称', '股票代码']]
        .dropna(subset=['股票代码'])
        .drop_duplicates(subset=['股票代码'])
    )
    code_to_name = dict(
        zip(
            stocks['股票代码'].astype(str).str.strip(),
            stocks['标的名称'].astype(str).str.strip(),
        )
    )
    logger.info(f"股票池：原始 {len(df)} 行 → 去重后 {len(code_to_name)} 只")
    return code_to_name


def load_and_normalize(symbols: list, period_years: int) -> pd.DataFrame:
    """使用 Duckdbloader 加载后复权收盘价并归一化（起始日 = 1.0）。"""
    from datafeed.dataloader import Duckdbloader

    end_date = date.today().strftime('%Y%m%d')
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

    df_pivot = df.pivot_table(index=df.index, columns='symbol', values='close')
    first_valid = df_pivot.apply(lambda col: col.dropna().iloc[0] if not col.dropna().empty else 1.0)
    df_norm = df_pivot.div(first_valid)

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


# ── Bokeh 图表构建 ────────────────────────────────────────────────────────────

def _make_colors(n: int) -> list:
    if n <= 2:
        return ['#1f77b4', '#ff7f0e'][:n]
    if n <= 20:
        return list(Category20[20])[:n]
    return list(turbo(n))


def build_chart(df_norm: pd.DataFrame, code_to_name: dict, period_years: int):
    """构建总览折线图，返回 (script, div, meta, n)。"""
    n = len(df_norm.columns)
    if n == 0:
        return '', '<p>无可用数据</p>', [], 0

    colors = _make_colors(n)
    p = figure(
        title=f"股票池近 {period_years} 年归一化后复权收盘价对比",
        x_axis_type='datetime',
        tools='pan,wheel_zoom,box_zoom,reset,save',
        active_drag='pan',
        active_scroll='wheel_zoom',
        sizing_mode='stretch_both',
    )
    p.title.text_font_size = '14px'
    p.title.text_font = 'Microsoft YaHei, Arial'
    p.xaxis.axis_label = '日期'
    p.yaxis.axis_label = '归一化收益（起始日 = 1.0）'
    p.xgrid.grid_line_color = '#e8e8e8'
    p.ygrid.grid_line_color = '#e8e8e8'

    x_vals = list(df_norm.index)
    meta = []
    for i, sym in enumerate(df_norm.columns):
        name = code_to_name.get(sym, sym)
        src = ColumnDataSource({
            'x':    x_vals,
            'y':    df_norm[sym].tolist(),
            'name': [name] * len(x_vals),
            'code': [sym]  * len(x_vals),
        })
        line = p.line('x', 'y', source=src, color=colors[i],
                      line_width=1.4, alpha=0.85, line_join='round')
        meta.append({'sym': sym, 'name': name, 'color': colors[i], 'id': line.id})

    p.add_tools(HoverTool(
        tooltips=[('日期', '@x{%F}'), ('股票', '@name（@code）'), ('相对收益', '@y{0.0000}')],
        formatters={'@x': 'datetime'},
        mode='mouse',
    ))
    script, div = components(p)
    return script, div, meta, n


def build_industry_fig(df_sub: pd.DataFrame, code_to_name: dict,
                       ind_name: str, period_years: int):
    """生成单个行业的 Bokeh figure（带内置可交互图例）。"""
    n = len(df_sub.columns)
    colors = _make_colors(n)

    p = figure(
        title=f"{ind_name}   ({n} 只)",
        x_axis_type='datetime',
        sizing_mode='stretch_width',
        height=360,
        tools='pan,wheel_zoom,reset,save',
        active_scroll='wheel_zoom',
    )
    p.title.text_font_size = '13px'
    p.title.text_font = 'Microsoft YaHei, Arial'
    p.xaxis.axis_label = '日期'
    p.yaxis.axis_label = '归一化收益'
    p.xgrid.grid_line_color = '#eeeeee'
    p.ygrid.grid_line_color = '#eeeeee'

    x_vals = list(df_sub.index)
    for i, sym in enumerate(df_sub.columns):
        name = code_to_name.get(sym, sym)
        src = ColumnDataSource({
            'x':    x_vals,
            'y':    df_sub[sym].tolist(),
            'name': [name] * len(x_vals),
            'code': [sym]  * len(x_vals),
        })
        p.line('x', 'y', source=src, color=colors[i], line_width=1.5, alpha=0.85,
               legend_label=f"{name}（{sym}）")

    p.add_tools(HoverTool(
        tooltips=[('日期', '@x{%F}'), ('股票', '@name'), ('相对收益', '@y{0.0000}')],
        formatters={'@x': 'datetime'},
        mode='mouse',
    ))
    p.legend.click_policy = 'hide'
    p.legend.label_text_font_size = '9px'
    p.legend.label_text_font = 'Microsoft YaHei, Arial'
    p.legend.location = 'top_left'
    p.legend.background_fill_alpha = 0.7
    return p


# ── HTML 页面生成 ─────────────────────────────────────────────────────────────

def build_chart_page(script: str, div: str, meta: list,
                     stock_count: int, period: int) -> str:
    js_tags  = CDN.render_js()
    css_tags = CDN.render_css()
    meta_json = json.dumps(
        {m['sym']: {'id': m['id'], 'color': m['color'], 'name': m['name']} for m in meta},
        ensure_ascii=False,
    )
    items_html = '\n'.join(
        f'''<label class="stock-item" data-search="{m['name'].lower()} {m['sym'].lower()}">
              <input type="checkbox" class="stock-cb" data-sym="{m['sym']}" checked>
              <span class="swatch" style="background:{m['color']}"></span>
              <span class="stock-label" title="{m['name']}（{m['sym']}）">{m['name']}<br>
                <small>{m['sym']}</small></span>
            </label>'''
        for m in meta
    )
    nav = build_nav('chart', period, f'共 {stock_count} 只 · 后复权 · 归一化')

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>股票池趋势图 · 近{period}年</title>
{css_tags}
<style>
{NAV_CSS}
  html, body {{ height: 100%; overflow: hidden; }}
  .sa-nav {{ position: fixed; }}
  .sa-main {{
    display: flex; position: fixed;
    top: 44px; left: 0; right: 0; bottom: 0;
  }}
  .chart-panel {{ flex: 0 0 75%; height: 100%; overflow: hidden; }}
  .chart-panel .bk-root {{ width: 100% !important; height: 100% !important; }}
  .legend-panel {{
    flex: 0 0 25%; height: 100%;
    display: flex; flex-direction: column;
    background: #f8f9fa; border-left: 1px solid #dee2e6;
  }}
  .legend-toolbar {{
    padding: 8px 10px; border-bottom: 1px solid #dee2e6;
    background: #fff; flex-shrink: 0;
  }}
  .search-box {{
    width: 100%; padding: 5px 8px; border: 1px solid #ccc;
    border-radius: 4px; font-size: 12px; margin-bottom: 6px;
    font-family: inherit;
  }}
  .search-box:focus {{ outline: none; border-color: #89b4fa; }}
  .btn-group {{ display: flex; gap: 6px; }}
  .ctrl-btn {{
    flex: 1; padding: 4px 0; font-size: 11px; cursor: pointer;
    border: 1px solid #ccc; border-radius: 4px; background: #fff;
    transition: background .15s;
  }}
  .ctrl-btn:hover {{ background: #e9ecef; }}
  .legend-list {{ flex: 1; overflow-y: auto; padding: 4px 0; }}
  .stock-item {{
    display: flex; align-items: center; gap: 6px;
    padding: 4px 10px; cursor: pointer; transition: background .1s; line-height: 1.3;
  }}
  .stock-item:hover {{ background: #e9ecef; }}
  .stock-item input[type=checkbox] {{ flex-shrink: 0; cursor: pointer; }}
  .swatch {{ width: 16px; height: 4px; border-radius: 2px; flex-shrink: 0; }}
  .stock-label {{ font-size: 12px; color: #333; min-width: 0; }}
  .stock-label small {{ color: #888; font-size: 10px; }}
  .stock-item.hidden {{ display: none; }}
</style>
</head>
<body>
{nav}
<div class="sa-main">
  <div class="chart-panel">{div}</div>
  <div class="legend-panel">
    <div class="legend-toolbar">
      <input class="search-box" id="searchBox" type="text" placeholder="🔍 搜索股票名称或代码...">
      <div class="btn-group">
        <button class="ctrl-btn" onclick="setAll(true)">✅ 全选</button>
        <button class="ctrl-btn" onclick="setAll(false)">⬜ 全不选</button>
        <button class="ctrl-btn" onclick="invertAll()">🔄 反选</button>
      </div>
    </div>
    <div class="legend-list" id="legendList">{items_html}</div>
  </div>
</div>
{js_tags}
{script}
<script>
(function() {{
  var META = {meta_json};
  function waitBokeh(cb, maxMs) {{
    maxMs = maxMs || 8000;
    var t0 = Date.now();
    (function check() {{
      if (typeof Bokeh !== 'undefined' && Bokeh.documents && Bokeh.documents.length > 0) {{
        cb(Bokeh.documents[0]);
      }} else if (Date.now() - t0 < maxMs) {{
        requestAnimationFrame(check);
      }}
    }})();
  }}
  waitBokeh(function(doc) {{
    document.querySelectorAll('.stock-cb').forEach(function(cb) {{
      var m = META[cb.dataset.sym];
      if (!m) return;
      var rdr = doc.get_model_by_id(m.id);
      if (!rdr) return;
      cb.addEventListener('change', function() {{ rdr.visible = cb.checked; }});
    }});
  }});
  function setAll(checked) {{
    document.querySelectorAll('.stock-item:not(.hidden) .stock-cb').forEach(function(cb) {{
      if (cb.checked !== checked) {{ cb.checked = checked; cb.dispatchEvent(new Event('change')); }}
    }});
  }}
  function invertAll() {{
    document.querySelectorAll('.stock-item:not(.hidden) .stock-cb').forEach(function(cb) {{
      cb.checked = !cb.checked; cb.dispatchEvent(new Event('change'));
    }});
  }}
  window.setAll = setAll; window.invertAll = invertAll;
  document.getElementById('searchBox').addEventListener('input', function() {{
    var q = this.value.toLowerCase().trim();
    document.querySelectorAll('.stock-item').forEach(function(item) {{
      item.classList.toggle('hidden', q !== '' && !(item.dataset.search || '').includes(q));
    }});
  }});
}})();
</script>
</body>
</html>"""


def build_industry_page(df_norm: pd.DataFrame, code_to_name: dict,
                         ind_map: dict, period: int) -> str:
    """按申万L1行业分组，生成多图页面 HTML 字符串。"""
    groups: dict = {}
    for sym in df_norm.columns:
        groups.setdefault(ind_map.get(sym, '未分类'), []).append(sym)

    sorted_groups = sorted(groups.items(), key=lambda x: -len(x[1]))
    logger.info(f"行业分组完成：{len(sorted_groups)} 个行业")

    figures, fig_meta = [], []
    for ind_name, syms in sorted_groups:
        figures.append(build_industry_fig(df_norm[syms], code_to_name, ind_name, period))
        fig_meta.append((ind_name, len(syms)))

    script, divs = components(figures)
    total = len(df_norm.columns)

    js_tags  = CDN.render_js()
    css_tags = CDN.render_css()
    nav = build_nav('industry', period, f'共 {total} 只 · 申万L1行业分组 · 后复权 · 归一化')

    cards_html = ''.join(
        f'<div class="ind-card">'
        f'<div class="ind-header">{ind_name} <span class="ind-count">{count} 只</span></div>'
        f'{div}</div>'
        for (ind_name, count), div in zip(fig_meta, divs)
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>行业趋势视图 · 近{period}年</title>
{css_tags}
<style>
{NAV_CSS}
  html, body {{ background: #f0f2f5; }}
  .ind-grid {{
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 14px; padding: 56px 16px 24px;
  }}
  .ind-card {{
    background: #fff; border: 1px solid #dee2e6;
    border-radius: 8px; overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
  }}
  .ind-header {{
    padding: 8px 12px 4px; font-size: 13px;
    font-weight: bold; color: #333; border-bottom: 1px solid #f0f0f0;
  }}
  .ind-count {{ font-size: 11px; font-weight: normal; color: #888; margin-left: 6px; }}
  @media (max-width: 900px) {{ .ind-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
{nav}
<div class="ind-grid">{cards_html}</div>
{js_tags}
{script}
</body>
</html>"""


# ── Handler 类 ────────────────────────────────────────────────────────────────

class ChartHandler:
    """
    处理 /chart 和 /industry 请求。
    在服务启动时通过 init() 注入股票池数据。
    """

    def __init__(self):
        self.code_to_name: dict = {}
        self.symbols: list = []

    def init(self, xlsx_path: str):
        self.code_to_name = load_stockpool(xlsx_path)
        self.symbols = list(self.code_to_name.keys())

    # ── /chart ─────────────────────────────────────────────────────────────

    def handle_chart(self, period: int) -> str:
        if not chart_cache.has(period):
            df_norm = load_and_normalize(self.symbols, period)
            data = build_chart(df_norm, self.code_to_name, period)
            chart_cache.set(period, data)

        script, div, meta, count = chart_cache.get(period)
        return build_chart_page(script, div, meta, count, period)

    # ── /industry ───────────────────────────────────────────────────────────

    def handle_industry(self, period: int) -> str:
        if not industry_cache.has(period):
            df_norm = load_and_normalize(self.symbols, period)
            ind_map = load_industry_map(self.symbols)
            html = build_industry_page(df_norm, self.code_to_name, ind_map, period)
            industry_cache.set(period, html)

        return industry_cache.get(period)
