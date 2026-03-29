"""
回测 Handler

路由：
  GET  /backtest                  → 策略列表页（列出 data/projs/*.toml）
  POST /backtest/run              → 触发回测，JSON body: {"toml_name": "xxx.toml"}
                                    返回 JSON: {"task_id": "..."}
  GET  /backtest/status/<task_id> → 轮询状态，返回 JSON: {"status": ..., "progress": ...}
  GET  /backtest/result/<task_id> → 等待中页面（轮询后自动展示结果）或完整结果 HTML
"""
import json
import threading
import time
import traceback
import uuid
from pathlib import Path

from loguru import logger

from web_service.ui import NAV_CSS, build_nav

# 项目根目录
_ROOT = Path(__file__).parent.parent.parent
_PROJS_DIR = _ROOT / 'data' / 'projs'


# ── 任务状态存储（内存，进程级别）───────────────────────────────────────────────

# {task_id: {'status': 'running'|'done'|'error',
#            'progress': float,
#            'html': str,       # 完整结果 HTML（done 时）
#            'error': str,      # 错误信息（error 时）
#            'toml_name': str,
#            'start_time': float}}
_tasks: dict = {}
_tasks_lock = threading.Lock()


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
        proj = from_toml(str(toml_path))
        observer = _Observer(task_id)
        engine = Engine(proj, global_observer=observer)
        engine.run()
        engine.analysis(console=False)     # 通过 observer 推送 HTML

        # 若 analysis 没有通过 observer 推送（console=True 模式兜底），直接生成
        with _tasks_lock:
            task = _tasks.get(task_id, {})
        if not task.get('html'):
            # 生成简单结果页
            _update_task(task_id, html=_simple_done_html(toml_path.stem))

        _update_task(task_id, status='done', progress=1.0)
        logger.info(f"[{task_id}] 回测完成")

    except Exception:
        err = traceback.format_exc()
        logger.error(f"[{task_id}] 回测出错:\n{err}")
        _update_task(task_id, status='error', error=err)


def _simple_done_html(name: str) -> str:
    return f"<html><body><h2>{name} 回测完成</h2><p>结果已生成，请查看控制台输出。</p></body></html>"


# ── 列表页 HTML ────────────────────────────────────────────────────────────────

def _list_toml_files() -> list[Path]:
    if not _PROJS_DIR.exists():
        return []
    return sorted(_PROJS_DIR.glob('*.toml'))


def _build_list_page() -> str:
    toml_files = _list_toml_files()
    nav = build_nav('backtest')

    if not toml_files:
        cards_html = '<p class="empty">data/projs/ 目录下暂无策略文件（*.toml）</p>'
    else:
        cards_html = ''.join(
            f'''<div class="proj-card">
              <div class="proj-name">{f.stem}</div>
              <div class="proj-file">{f.name}</div>
              <button class="run-btn" onclick="runBacktest('{f.name}')">▶ 运行回测</button>
            </div>'''
            for f in toml_files
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>回测 · 策略列表</title>
<style>
{NAV_CSS}
  html, body {{ background: #f0f2f5; min-height: 100%; }}
  .page-body {{
    padding: 60px 24px 24px;
    max-width: 960px; margin: 0 auto;
  }}
  h2 {{ font-size: 18px; color: #333; margin-bottom: 16px; }}
  .proj-grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 14px;
  }}
  .proj-card {{
    background: #fff; border: 1px solid #dee2e6; border-radius: 8px;
    padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.06);
    display: flex; flex-direction: column; gap: 8px;
  }}
  .proj-name {{ font-size: 14px; font-weight: bold; color: #333; }}
  .proj-file {{ font-size: 11px; color: #888; }}
  .run-btn {{
    margin-top: auto; padding: 7px 0; background: #cba6f7;
    color: #1e1e2e; border: none; border-radius: 5px;
    font-size: 13px; font-weight: bold; cursor: pointer;
    transition: background .15s;
  }}
  .run-btn:hover {{ background: #b07de0; }}
  .run-btn:disabled {{ background: #ccc; cursor: not-allowed; }}
  .empty {{ color: #888; font-size: 14px; }}
  /* 运行中覆盖层 */
  #overlay {{
    display: none; position: fixed; inset: 0;
    background: rgba(30,30,46,.75); z-index: 99999;
    flex-direction: column; align-items: center; justify-content: center;
    color: #cdd6f4; font-size: 15px; gap: 16px;
  }}
  #overlay.show {{ display: flex; }}
  .spinner {{
    width: 40px; height: 40px; border: 4px solid #45475a;
    border-top-color: #cba6f7; border-radius: 50%;
    animation: spin .8s linear infinite;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  .progress-bar-wrap {{
    width: 280px; height: 8px; background: #45475a; border-radius: 4px; overflow: hidden;
  }}
  #progressBar {{ height: 100%; background: #cba6f7; width: 0; transition: width .3s; }}
  #statusMsg {{ font-size: 13px; color: #a6adc8; }}
</style>
</head>
<body>
{nav}
<div class="page-body">
  <h2>策略项目</h2>
  <div class="proj-grid">{cards_html}</div>
</div>

<!-- 运行中蒙层 -->
<div id="overlay">
  <div class="spinner"></div>
  <div id="overlayTitle">正在运行回测...</div>
  <div class="progress-bar-wrap"><div id="progressBar"></div></div>
  <div id="statusMsg">0%</div>
</div>

<script>
function runBacktest(tomlName) {{
  // 禁用所有按钮，显示蒙层
  document.querySelectorAll('.run-btn').forEach(function(b) {{ b.disabled = true; }});
  document.getElementById('overlayTitle').textContent = '正在运行：' + tomlName.replace('.toml','');
  document.getElementById('overlay').classList.add('show');

  fetch('/backtest/run', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{toml_name: tomlName}}),
  }})
  .then(function(r) {{ return r.json(); }})
  .then(function(data) {{
    if (data.task_id) {{
      pollStatus(data.task_id);
    }} else {{
      alert('启动失败：' + (data.error || '未知错误'));
      resetOverlay();
    }}
  }})
  .catch(function(e) {{ alert('请求失败：' + e); resetOverlay(); }});
}}

function pollStatus(taskId) {{
  var interval = setInterval(function() {{
    fetch('/backtest/status/' + taskId)
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      var pct = Math.round((data.progress || 0) * 100);
      document.getElementById('progressBar').style.width = pct + '%';
      document.getElementById('statusMsg').textContent = pct + '%';

      if (data.status === 'done') {{
        clearInterval(interval);
        window.location.href = '/backtest/result/' + taskId;
      }} else if (data.status === 'error') {{
        clearInterval(interval);
        alert('回测出错，请查看控制台日志。');
        resetOverlay();
      }}
    }})
    .catch(function() {{ clearInterval(interval); resetOverlay(); }});
  }}, 800);
}}

function resetOverlay() {{
  document.getElementById('overlay').classList.remove('show');
  document.querySelectorAll('.run-btn').forEach(function(b) {{ b.disabled = false; }});
}}
</script>
</body>
</html>"""


# ── Handler 类 ────────────────────────────────────────────────────────────────

class BacktestHandler:

    def handle_list(self) -> str:
        """GET /backtest → 策略列表页"""
        return _build_list_page()

    def handle_run(self, body: bytes) -> tuple[int, dict]:
        """POST /backtest/run → 触发回测，返回 (http_status, json_dict)"""
        try:
            payload = json.loads(body.decode('utf-8'))
        except Exception:
            return 400, {'error': '请求体必须是合法的 JSON'}

        toml_name = payload.get('toml_name', '').strip()
        if not toml_name:
            return 400, {'error': '缺少 toml_name 字段'}

        toml_path = _PROJS_DIR / toml_name
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

    def handle_status(self, task_id: str) -> tuple[int, dict]:
        """GET /backtest/status/<task_id> → 返回当前状态"""
        with _tasks_lock:
            task = _tasks.get(task_id)
        if task is None:
            return 404, {'error': '任务不存在'}
        return 200, {
            'status':   task['status'],
            'progress': task['progress'],
            'error':    task.get('error', ''),
        }

    def handle_result(self, task_id: str) -> tuple[int, str]:
        """GET /backtest/result/<task_id> → 结果 HTML 或等待页"""
        with _tasks_lock:
            task = _tasks.get(task_id)

        if task is None:
            return 404, '<h2>任务不存在或已过期</h2>'

        if task['status'] == 'running':
            return 200, self._waiting_page(task_id, task['toml_name'])

        if task['status'] == 'error':
            return 200, self._error_page(task['error'], task['toml_name'])

        # done：返回 Bokeh 结果 HTML（已是完整 file_html 文档）
        html = task['html']
        # 在结果页顶部注入返回按钮
        back_btn = (
            '<div style="position:fixed;top:8px;left:12px;z-index:9999;">'
            '<a href="/backtest" style="background:#cba6f7;color:#1e1e2e;padding:5px 14px;'
            'border-radius:5px;text-decoration:none;font-size:12px;font-weight:bold;">'
            '← 返回列表</a></div>'
        )
        html = html.replace('<body>', '<body>' + back_btn, 1)
        return 200, html

    # ── 辅助页面 ────────────────────────────────────────────────────────────

    @staticmethod
    def _waiting_page(task_id: str, toml_name: str) -> str:
        nav = build_nav('backtest')
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>回测运行中...</title>
<style>
{NAV_CSS}
  html, body {{ background: #1e1e2e; color: #cdd6f4; height: 100%;
    display: flex; flex-direction: column; }}
  .center {{
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 20px;
  }}
  .spinner {{
    width: 48px; height: 48px; border: 5px solid #45475a;
    border-top-color: #cba6f7; border-radius: 50%;
    animation: spin .8s linear infinite;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  .title {{ font-size: 16px; color: #cba6f7; font-weight: bold; }}
  .sub   {{ font-size: 13px; color: #a6adc8; }}
  .progress-bar-wrap {{
    width: 320px; height: 8px; background: #313244; border-radius: 4px; overflow: hidden;
  }}
  #progressBar {{ height: 100%; background: #cba6f7; width: 0; transition: width .4s; }}
  #pct {{ font-size: 13px; color: #a6adc8; }}
</style>
</head>
<body>
{nav}
<div class="center">
  <div class="spinner"></div>
  <div class="title">正在运行：{toml_name.replace('.toml', '')}</div>
  <div class="progress-bar-wrap"><div id="progressBar"></div></div>
  <div id="pct" class="sub">0%</div>
</div>
<script>
(function poll() {{
  fetch('/backtest/status/{task_id}')
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      var pct = Math.round((data.progress || 0) * 100);
      document.getElementById('progressBar').style.width = pct + '%';
      document.getElementById('pct').textContent = pct + '%';
      if (data.status === 'done') {{
        window.location.href = '/backtest/result/{task_id}';
      }} else if (data.status === 'error') {{
        window.location.href = '/backtest/result/{task_id}';
      }} else {{
        setTimeout(poll, 800);
      }}
    }})
    .catch(function() {{ setTimeout(poll, 2000); }});
}})();
</script>
</body>
</html>"""

    @staticmethod
    def _error_page(error: str, toml_name: str) -> str:
        nav = build_nav('backtest')
        safe_err = error.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>回测出错</title>
<style>
{NAV_CSS}
  html, body {{ background: #f0f2f5; }}
  .page-body {{ padding: 60px 24px 24px; max-width: 860px; margin: 0 auto; }}
  h2 {{ color: #d20f39; margin-bottom: 12px; }}
  pre {{ background: #1e1e2e; color: #f38ba8; padding: 16px; border-radius: 8px;
         font-size: 12px; overflow: auto; }}
  .back {{ display: inline-block; margin-top: 16px; padding: 7px 18px;
           background: #cba6f7; color: #1e1e2e; border-radius: 5px;
           text-decoration: none; font-weight: bold; font-size: 13px; }}
</style>
</head>
<body>
{nav}
<div class="page-body">
  <h2>回测出错：{toml_name}</h2>
  <pre>{safe_err}</pre>
  <a class="back" href="/backtest">← 返回列表</a>
</div>
</body>
</html>"""
