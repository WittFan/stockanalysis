"""
健康检查接口

GET /api/health → {"status": "ok"}

供 Electron 主进程轮询，判断 Flask 后端是否已就绪。
响应必须轻量（无 DB 查询），仅表示进程存活。
"""
from flask import Blueprint, jsonify

bp = Blueprint('health', __name__)


@bp.get('/health')
def health():
    return jsonify({'status': 'ok'})
