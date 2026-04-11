"""
回测 Handler

路由（Flask API）：
  GET  /api/backtest/list             → JSON {strategies: [{name, file}]}
  POST /api/backtest/run              → JSON {task_id} 或 {error}
  GET  /api/backtest/status/<task_id> → JSON {status, progress, error}
  GET  /api/backtest/result/<task_id> → JSON {status, html} 或 {status, error}
"""
import json
import threading
import time
import traceback
import uuid
from pathlib import Path

from loguru import logger

# 项目根目录（默认值，正常通过 BacktestHandler(root_path=...) 注入）
_DEFAULT_ROOT = Path(__file__).parent.parent.parent


# ── 任务状态存储（内存，进程级别）───────────────────────────────────────────────

# {task_id: {'status': 'running'|'done'|'error',
#            'progress': float,
#            'html': str,
#            'error': str,
#            'toml_name': str,
#            'start_time': float}}
_tasks: dict      = {}
_tasks_lock       = threading.Lock()


class _Observer:
    """传入 Engine，接收进度和结果通知。"""
    def __init__(self, task_id: str):
        self._task_id = task_id

    def notify(self, data: dict):
        msg_type = data.get('msg_type')
        if msg_type == 'ON_BAR':
            _update_task(self._task_id, progress=data.get('progress', 0))
        elif msg_type == 'HTML':
            _update_task(self._task_id, html=data.get('html', ''))


def _update_task(task_id: str, **kwargs):
    with _tasks_lock:
        if task_id in _tasks:
            _tasks[task_id].update(kwargs)


def _run_backtest(task_id: str, toml_path: Path):
    """在后台线程中执行回测。"""
    try:
        from engine.proj_config import from_toml
        from engine.strategy import Engine

        logger.info(f"[{task_id}] 开始回测: {toml_path.name}")
        proj     = from_toml(str(toml_path))
        observer = _Observer(task_id)
        engine   = Engine(proj, global_observer=observer)
        engine.run()
        engine.analysis(console=False)

        with _tasks_lock:
            task = _tasks.get(task_id, {})
        if not task.get('html'):
            _update_task(task_id, html=f"<html><body><h2>{toml_path.stem} 回测完成</h2></body></html>")

        _update_task(task_id, status='done', progress=1.0)
        logger.info(f"[{task_id}] 回测完成")

    except Exception:
        err = traceback.format_exc()
        logger.error(f"[{task_id}] 回测出错:\n{err}")
        _update_task(task_id, status='error', error=err)


# ── Handler 类 ────────────────────────────────────────────────────────────────

class BacktestHandler:

    def __init__(self, root_path: Path = None):
        """
        :param root_path: 项目根目录（由 create_app 注入，避免脆弱的 __file__ 上溯）。
                          未传时退回到 _DEFAULT_ROOT（3层上溯），兼容直接实例化场景。
        """
        root = Path(root_path) if root_path is not None else _DEFAULT_ROOT
        self._projs_dir = root / 'data' / 'projs'

    def _list_toml_files(self) -> list:
        if not self._projs_dir.exists():
            return []
        return sorted(self._projs_dir.glob('*.toml'))

    def handle_list(self) -> dict:
        """GET /api/backtest/list → {strategies: [{name, file}]}"""
        return {
            'strategies': [
                {'name': f.stem, 'file': f.name}
                for f in self._list_toml_files()
            ]
        }

    def handle_run(self, body: bytes) -> tuple:
        """POST /api/backtest/run → (http_status, {task_id} 或 {error})"""
        try:
            payload = json.loads(body.decode('utf-8'))
        except Exception:
            return 400, {'error': '请求体必须是合法的 JSON'}

        toml_name = payload.get('toml_name', '').strip()
        if not toml_name:
            return 400, {'error': '缺少 toml_name 字段'}

        toml_path = self._projs_dir / toml_name
        if not toml_path.exists():
            return 404, {'error': f'找不到策略文件: {toml_name}'}

        task_id = uuid.uuid4().hex
        with _tasks_lock:
            _tasks[task_id] = {
                'status':     'running',
                'progress':   0.0,
                'html':       '',
                'error':      '',
                'toml_name':  toml_name,
                'start_time': time.time(),
            }

        t = threading.Thread(target=_run_backtest, args=(task_id, toml_path), daemon=True)
        t.start()
        logger.info(f"回测任务已启动 task_id={task_id} toml={toml_name}")
        return 200, {'task_id': task_id}

    def handle_status(self, task_id: str) -> tuple:
        """GET /api/backtest/status/<task_id> → (http_status, {status, progress, error})"""
        with _tasks_lock:
            task = _tasks.get(task_id)
        if task is None:
            return 404, {'error': '任务不存在'}
        return 200, {
            'status':   task['status'],
            'progress': task['progress'],
            'error':    task.get('error', ''),
        }

    def handle_result(self, task_id: str) -> tuple:
        """GET /api/backtest/result/<task_id> → (http_status, {status, ...})"""
        with _tasks_lock:
            task = _tasks.get(task_id)

        if task is None:
            return 404, {'status': 'error', 'error': '任务不存在或已过期'}

        if task['status'] == 'running':
            return 200, {'status': 'running', 'progress': task['progress']}

        if task['status'] == 'error':
            return 200, {'status': 'error', 'error': task['error']}

        # done：返回完整 HTML（Bokeh file_html，由 engine.analysis 生成）
        return 200, {'status': 'done', 'html': task['html']}
