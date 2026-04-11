"""
量化投研平台 Web 服务入口（前后端分离版）

用法：
    python run.py                  # 默认 8888 端口
    python run.py --port 9000
    python run.py --no-stockpool   # 不加载股票池

开发模式（前后端分开运行）：
    终端1: python run.py           # Flask 后端，端口 8888
    终端2: cd frontend && npm run dev  # Vite 前端，端口 5173

生产模式（前端已构建）：
    cd frontend && npm run build
    python run.py                  # Flask 同时托管前端
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loguru import logger
from api.app import create_app


def main():
    parser = argparse.ArgumentParser(description='量化投研平台 Web 服务')
    parser.add_argument('--port',         type=int, default=8888)
    parser.add_argument('--no-stockpool', action='store_true')
    args = parser.parse_args()

    xlsx_path = None
    if not args.no_stockpool:
        xlsx_path = str(ROOT / 'stockpool.xlsx')

    app = create_app(xlsx_path=xlsx_path)

    dist_exists = (ROOT / 'frontend' / 'dist').exists()

    logger.info('─' * 52)
    logger.info(f'量化投研平台已启动 → http://localhost:{args.port}')
    if dist_exists:
        logger.info('模式：生产（Flask 托管前端）')
    else:
        logger.info('模式：开发（前端请运行 cd frontend && npm run dev）')
        logger.info('前端地址 → http://localhost:5173')
    logger.info('API 接口：')
    logger.info('  GET  /api/chart?period={1|2|3}')
    logger.info('  GET  /api/industry?period={1|2|3}')
    logger.info('  GET  /api/value/data?year=&metric=')
    logger.info('  GET  /api/backtest/list')
    logger.info('  POST /api/backtest/run')
    logger.info('按 Ctrl+C 停止')
    logger.info('─' * 52)

    app.run(host='0.0.0.0', port=args.port, debug=False, threaded=True)


if __name__ == '__main__':
    main()
