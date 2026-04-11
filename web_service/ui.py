"""
公共 UI 组件：导航栏 CSS 与 HTML 构建函数。
所有页面复用同一套视觉风格（Catppuccin Mocha 配色）。
"""

# ── 导航栏 + 基础 CSS（所有页面共享）─────────────────────────────────────────
NAV_CSS = """
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body {
    font-family: 'Microsoft YaHei', 'PingFang SC', Arial, sans-serif;
  }
  .sa-nav {
    position: sticky; top: 0; z-index: 9999; height: 44px;
    background: #1e1e2e; color: #cdd6f4;
    display: flex; align-items: center; gap: 10px; padding: 0 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,.5); font-size: 13px;
  }
  .sa-nav .logo  { font-size: 15px; font-weight: bold; color: #cba6f7; }
  .sa-nav .info  { color: #a6adc8; font-size: 11px; }
  .sa-nav .spacer { flex: 1; }
  .sa-nav .sep   { color: #45475a; margin: 0 4px; }
  .sa-nav .hint  { color: #585b70; font-size: 11px; }
  .nav-btn {
    color: #89b4fa; text-decoration: none;
    padding: 3px 12px; border-radius: 5px; border: 1px solid #45475a;
    transition: background .15s; font-size: 12px;
  }
  .nav-btn:hover  { background: #313244; }
  .nav-btn.active {
    background: #cba6f7; border-color: #cba6f7;
    color: #1e1e2e; font-weight: bold;
  }
"""


def build_nav(active: str = '', period: int = 3, info: str = '') -> str:
    """
    生成顶部导航栏 HTML。
    active: 当前激活的视图名，取值 'chart' | 'industry' | 'backtest' | 'value'
    period: 保留参数（供页面内部生成跳转链接使用，导航栏本身不再显示年度按钮）
    info:   导航栏副标题文字
    """
    def _view_btn(name, label, href):
        cls = ' active' if active == name else ''
        return f'<a href="{href}" class="nav-btn{cls}">{label}</a>'

    info_html = f'<span class="info">{info}</span>' if info else ''

    return f"""
<nav class="sa-nav">
  <span class="logo">📈 量化投研平台</span>
  {info_html}
  <span class="sep">|</span>
  {_view_btn('chart',    '📊 总览',  f'/chart?period={period}')}
  {_view_btn('industry', '🗂 行业',  f'/industry?period={period}')}
  {_view_btn('backtest', '🔬 回测',  '/backtest')}
  {_view_btn('value',    '🎯 价值',  '/value')}
  <span class="spacer"></span>
</nav>"""
