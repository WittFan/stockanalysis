"""
助理智能体路由

POST /api/assistant/chat  → SSE 流式响应（OpenAI 格式）
GET  /api/assistant/status → 检查 kimi CLI 是否可用
"""
from flask import Blueprint, Response, jsonify, request

from api.handlers.kimi_wire_handler import KimiWireHandler, KimiWireSession

bp = Blueprint('assistant', __name__)
_handler = KimiWireHandler()


@bp.get('/assistant/status')
def status():
    """检查本机是否安装了 kimi CLI"""
    session = KimiWireSession()
    kimi_path = session._find_kimi()
    return jsonify({
        'kimi_available': kimi_path is not None,
        'kimi_path': kimi_path,
    })


@bp.post('/assistant/chat')
def chat():
    """
    接收 OpenAI 格式请求，通过 kimi --wire 子进程流式返回响应。

    请求体：
    {
      "messages": [{"role": "user", "content": "..."}],
      "system": "系统提示词（可选）"
    }

    响应：text/event-stream，OpenAI SSE 格式
    """
    data = request.get_json(force=True) or {}
    messages = data.get('messages', [])
    system = data.get('system', '')

    if not messages:
        return jsonify({'error': 'messages 不能为空'}), 400

    def generate():
        yield from _handler.chat_stream(messages, system)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )
