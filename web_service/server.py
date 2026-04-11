"""
量化投研平台 Web 服务主入口

用法:
    python web_service/server.py                     # 默认端口 8888
    python web_service/server.py --port 9000
    python web_service/server.py --no-stockpool      # 不加载股票池（仅回测功能）

路由:
    GET  /                           → 302 跳转 /chart?period=3
    GET  /chart?period={1|2|3}       → 股票池总览趋势图
    GET  /industry?period={1|2|3}    → 申万L1行业分组图
    GET  /backtest                   → 策略列表页
    POST /backtest/run               → 触发回测
    GET  /backtest/status/<task_id>  → 轮询回测进度
    GET  /backtest/result/<task_id>  → 回测结果页
"""
import argparse
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from loguru import logger

# 确保项目根目录在 sys.path
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web_service.handlers.chart_handler import ChartHandler
from web_service.handlers.backtest_handler import BacktestHandler
from web_service.handlers.value_matrix_handler import ValueMatrixHandler

# 全局 handler 实例（服务生命周期内复用）
_chart_handler   = ChartHandler()
_backtest_handler = BacktestHandler()
_value_handler   = ValueMatrixHandler()


class PlatformHandler(BaseHTTPRequestHandler):
    """HTTP 请求路由分发器。"""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs     = urllib.parse.parse_qs(parsed.query)
        path   = parsed.path.rstrip('/')

        # ── / ──────────────────────────────────────────────────────────────
        if path in ('', '/'):
            self._redirect('/chart?period=3')
            return

        # ── /chart ─────────────────────────────────────────────────────────
        if path == '/chart':
            period = self._parse_period(qs)
            html = _chart_handler.handle_chart(period)
            self._send_html(html)
            return

        # ── /industry ───────────────────────────────────────────────────────
        if path == '/industry':
            period = self._parse_period(qs)
            html = _chart_handler.handle_industry(period)
            self._send_html(html)
            return

        # ── /value ─────────────────────────────────────────────────────────
        if path == '/value':
            html = _value_handler.handle_page(qs)
            self._send_html(html)
            return

        if path == '/value/data':
            code, data = _value_handler.handle_data_api(qs)
            self._send_json(code, data)
            return

        # ── /backtest（列表页）──────────────────────────────────────────────
        if path == '/backtest':
            html = _backtest_handler.handle_list()
            self._send_html(html)
            return

        # ── /backtest/status/<task_id> ──────────────────────────────────────
        if path.startswith('/backtest/status/'):
            task_id = path[len('/backtest/status/'):]
            code, data = _backtest_handler.handle_status(task_id)
            self._send_json(code, data)
            return

        # ── /backtest/result/<task_id> ──────────────────────────────────────
        if path.startswith('/backtest/result/'):
            task_id = path[len('/backtest/result/'):]
            code, html = _backtest_handler.handle_result(task_id)
            self._send_html(html, status=code)
            return

        self._send(404, 'text/plain; charset=utf-8', b'404 Not Found')

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path.rstrip('/')

        # ── POST /value/forecast ───────────────────────────────────────────
        if path == '/value/forecast':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length) if length else b'{}'
            code, data = _value_handler.handle_forecast(body)
            self._send_json(code, data)
            return

        # ── POST /backtest/run ──────────────────────────────────────────────
        if path == '/backtest/run':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length) if length else b'{}'
            code, data = _backtest_handler.handle_run(body)
            self._send_json(code, data)
            return

        self._send(404, 'text/plain; charset=utf-8', b'404 Not Found')

    # ── 辅助方法 ─────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_period(qs: dict, default: int = 3) -> int:
        try:
            p = int(qs.get('period', [str(default)])[0])
            return max(1, min(3, p))
        except ValueError:
            return default

    def _redirect(self, location: str):
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()

    def _send_html(self, html: str, status: int = 200):
        body = html.encode('utf-8')
        self._send(status, 'text/html; charset=utf-8', body)

    def _send_json(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self._send(status, 'application/json; charset=utf-8', body)

    def _send(self, code: int, content_type: str, body: bytes):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        logger.debug(f"HTTP {self.address_string()} {args[0]} → {args[1]}")


# ── 入口 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='量化投研平台 Web 服务')
    parser.add_argument('--port', type=int, default=8888, help='监听端口（默认 8888）')
    parser.add_argument('--no-stockpool', action='store_true',
                        help='不加载股票池（/chart、/industry 不可用）')
    args = parser.parse_args()

    # 初始化股票池
    if not args.no_stockpool:
        xlsx_path = str(ROOT / 'stockpool.xlsx')
        if Path(xlsx_path).exists():
            _chart_handler.init(xlsx_path)
            _value_handler.init(xlsx_path)
        else:
            logger.warning(f"未找到 stockpool.xlsx，/chart、/industry、/value 页面将不可用")

    server = ThreadingHTTPServer(('0.0.0.0', args.port), PlatformHandler)
    logger.info('─' * 52)
    logger.info(f'量化投研平台 Web 服务已启动 → http://localhost:{args.port}')
    logger.info(f'  /chart      股票池趋势图')
    logger.info(f'  /industry   行业分组图')
    logger.info(f'  /backtest   策略回测')
    logger.info(f'  /value      价值坐标系')
    logger.info('按 Ctrl+C 停止')
    logger.info('─' * 52)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('服务已停止')
        server.server_close()


if __name__ == '__main__':
    main()
