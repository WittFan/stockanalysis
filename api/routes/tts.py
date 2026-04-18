"""
TTS 语音合成路由 — 后端代理 Microsoft Edge TTS

POST /api/tts/speech  → 返回 audio/mpeg 音频流
"""
import asyncio

from flask import Blueprint, Response, jsonify, request

bp = Blueprint('tts', __name__)

# 尝试导入 edge_tts，未安装时 gracefully 处理
try:
    import edge_tts
    _EDGE_TTS_AVAILABLE = True
except ImportError:
    _EDGE_TTS_AVAILABLE = False
    edge_tts = None


# 常用中文 Edge TTS 语音列表（供前端展示）
EDGE_VOICES = [
    {'voice': 'zh-CN-XiaoxiaoNeural', 'name': '晓晓', 'desc': '温柔女性（推荐）'},
    {'voice': 'zh-CN-XiaoyiNeural', 'name': '晓伊', 'desc': '活泼女性'},
    {'voice': 'zh-CN-YunjianNeural', 'name': '云健', 'desc': '成熟男性'},
    {'voice': 'zh-CN-YunxiNeural', 'name': '云希', 'desc': '年轻男性'},
    {'voice': 'zh-CN-YunxiaNeural', 'name': '云夏', 'desc': '少年男性'},
    {'voice': 'zh-CN-liaoning-XiaobeiNeural', 'name': '晓北', 'desc': '东北话'},
    {'voice': 'zh-CN-shaanxi-XiaoniNeural', 'name': '晓妮', 'desc': '陕西话'},
]

# 情感风格映射（部分语音支持）
EDGE_STYLES = [
    {'id': 'default', 'name': '默认'},
    {'id': 'assistant', 'name': '助理'},
    {'id': 'chat', 'name': '闲聊'},
    {'id': 'cheerful', 'name': '开心'},
    {'id': 'sad', 'name': '悲伤'},
    {'id': 'angry', 'name': '生气'},
]


@bp.get('/tts/voices')
def list_voices():
    """返回可用的 Edge TTS 中文语音列表"""
    return jsonify({
        'voices': EDGE_VOICES,
        'styles': EDGE_STYLES,
        'available': _EDGE_TTS_AVAILABLE,
    })


@bp.post('/tts/speech')
def speech():
    """
    接收文本，通过 edge-tts 生成音频并返回。

    请求体：
    {
      "text": "你好，我是助理小姐",
      "voice": "zh-CN-XiaoxiaoNeural",
      "rate": "+0%",
      "pitch": "+0Hz",
      "style": "assistant"
    }
    """
    if not _EDGE_TTS_AVAILABLE:
        return jsonify({'error': 'edge-tts 未安装，请运行 pip install edge-tts'}), 503

    data = request.get_json(force=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'text 不能为空'}), 400

    voice = data.get('voice', 'zh-CN-XiaoxiaoNeural')
    rate = data.get('rate', '+0%')
    pitch = data.get('pitch', '+0Hz')
    style = data.get('style', 'default')

    # 构造 SSML（支持情感风格）
    if style and style != 'default':
        ssml = (
            '<speak xmlns="http://www.w3.org/2001/10/synthesis" '
            'xmlns:mstts="https://www.w3.org/2001/mstts" version="1.0">'
            f'<voice name="{voice}">'
            f'<mstts:express-as style="{style}">{text}</mstts:express-as>'
            f'</voice></speak>'
        )
    else:
        ssml = text

    async def _collect_audio():
        chunks = []
        communicate = edge_tts.Communicate(ssml, voice, rate=rate, pitch=pitch)
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                chunks.append(chunk['data'])
        return b''.join(chunks)

    try:
        audio_data = asyncio.run(_collect_audio())
    except Exception as e:
        return jsonify({'error': f'TTS 生成失败: {str(e)}'}), 502

    return Response(audio_data, mimetype='audio/mpeg')
