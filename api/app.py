"""
Flask 应用工厂

开发模式：
    python run.py
    cd frontend && npm run dev   # Vite dev server 代理 /api/* 到 Flask

生产模式（前端已构建）：
    cd frontend && npm run build
    python run.py                # Flask 同时托管 frontend/dist/

Electron 桌面端：
    electron/main.js 以子进程方式启动本服务，
    轮询 GET /api/health 确认就绪后再显示 BrowserWindow。
"""
from pathlib import Path

from flask import Flask
from flask_cors import CORS
from loguru import logger


def create_app(xlsx_path: str = None, root_path: Path = None) -> Flask:
    dist_dir = Path(__file__).parent.parent / 'frontend' / 'dist'
    app = Flask(
        __name__,
        static_folder=str(dist_dir) if dist_dir.exists() else None,
        static_url_path='',
    )
    CORS(app)

    # ── 初始化 handler ────────────────────────────────────────────────────────
    from api.handlers.chart_handler import ChartHandler
    from api.handlers.backtest_handler import BacktestHandler
    from api.handlers.value_matrix_handler import ValueMatrixHandler

    chart_handler    = ChartHandler()
    backtest_handler = BacktestHandler(root_path=root_path)
    value_handler    = ValueMatrixHandler()

    if xlsx_path and Path(xlsx_path).exists():
        chart_handler.init(xlsx_path)
        value_handler.init(xlsx_path)
        logger.info(f'股票池已加载：{xlsx_path}')
    else:
        logger.warning('未加载股票池，/api/chart 和 /api/industry 不可用')

    # ── 注册蓝图 ──────────────────────────────────────────────────────────────
    from api.routes.chart import make_chart_bp
    from api.routes.backtest import make_backtest_bp
    from api.routes.value import make_value_bp
    from api.routes.health import bp as health_bp

    app.register_blueprint(make_chart_bp(chart_handler),       url_prefix='/api')
    app.register_blueprint(make_backtest_bp(backtest_handler),  url_prefix='/api')
    app.register_blueprint(make_value_bp(value_handler),        url_prefix='/api')
    app.register_blueprint(health_bp,                           url_prefix='/api')

    # ── SPA fallback（生产模式：Flask 托管前端静态文件）──────────────────────
    if dist_dir.exists():
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def serve_spa(path):
            return app.send_static_file('index.html')
    else:
        @app.route('/')
        def dev_hint():
            return (
                '<h3>开发模式</h3>'
                '<p>前端请运行：<code>cd frontend &amp;&amp; npm run dev</code></p>'
                '<p>Electron：<code>npm run electron:dev</code></p>'
            )

    return app
