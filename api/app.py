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

from flask import Flask, send_from_directory
from flask_cors import CORS
from loguru import logger


def create_app(xlsx_path: str = None, root_path: Path = None) -> Flask:
    dist_dir = Path(__file__).parent.parent / 'desktop' / 'frontend' / 'dist'
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
    from api.handlers.download_handler import DownloadHandler

    chart_handler    = ChartHandler(xlsx_path=xlsx_path)
    backtest_handler = BacktestHandler(root_path=root_path)
    value_handler    = ValueMatrixHandler(xlsx_path=xlsx_path)
    download_handler = DownloadHandler()

    if xlsx_path and Path(xlsx_path).exists():
        logger.info(f'股票池配置就绪：{xlsx_path}（首次请求时加载）')
    else:
        logger.warning('未配置股票池，/api/chart 和 /api/industry 不可用')

    # ── 注册蓝图 ──────────────────────────────────────────────────────────────
    from api.routes.chart import make_chart_bp
    from api.routes.backtest import make_backtest_bp
    from api.routes.value import make_value_bp
    from api.routes.health import bp as health_bp
    from api.routes.download import make_download_bp
    from api.routes.assistant import bp as assistant_bp
    from api.routes.tts import bp as tts_bp
    from api.agent import make_agent_bp
    from api.agent.db import AgentDB
    from api.agent.tool_registry import build_default_registry

    app.register_blueprint(make_chart_bp(chart_handler),       url_prefix='/api')
    app.register_blueprint(make_backtest_bp(backtest_handler),  url_prefix='/api')
    app.register_blueprint(make_value_bp(value_handler),        url_prefix='/api')
    app.register_blueprint(health_bp,                           url_prefix='/api')
    app.register_blueprint(make_download_bp(download_handler),  url_prefix='/api')
    app.register_blueprint(assistant_bp,                        url_prefix='/api')
    app.register_blueprint(tts_bp,                              url_prefix='/api')

    agent_db = AgentDB()
    agent_db.create_tables()
    app.register_blueprint(make_agent_bp(agent_db, build_default_registry()), url_prefix='/api')

    # ── 模型文件（Electron 回落到 Flask 时直接提供 VRM/GLB）────────────────
    public_models = Path(__file__).parent.parent / 'desktop' / 'frontend' / 'public' / 'models'

    @app.route('/models/<path:filename>')
    def serve_model(filename):
        # 优先从 dist/models（生产），否则从 public/models（开发）
        dist_models = dist_dir / 'models'
        folder = str(dist_models) if dist_models.exists() else str(public_models)
        return send_from_directory(folder, filename)

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
