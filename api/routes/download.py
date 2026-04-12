from flask import Blueprint, jsonify, request


def make_download_bp(handler) -> Blueprint:
    bp = Blueprint('download', __name__)

    @bp.route('/download/tables')
    def download_tables():
        code, data = handler.handle_tables()
        return jsonify(data), code

    @bp.route('/download/start', methods=['POST'])
    def download_start():
        body = request.get_json(force=True, silent=True) or {}
        code, data = handler.handle_start(body)
        return jsonify(data), code

    @bp.route('/download/status/<task_id>')
    def download_status(task_id):
        code, data = handler.handle_status(task_id)
        return jsonify(data), code

    return bp
