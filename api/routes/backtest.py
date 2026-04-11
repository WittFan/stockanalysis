from flask import Blueprint, jsonify, request


def make_backtest_bp(handler) -> Blueprint:
    bp = Blueprint('backtest', __name__)

    @bp.route('/backtest/list')
    def backtest_list():
        return jsonify(handler.handle_list())

    @bp.route('/backtest/run', methods=['POST'])
    def backtest_run():
        code, data = handler.handle_run(request.get_data())
        return jsonify(data), code

    @bp.route('/backtest/status/<task_id>')
    def backtest_status(task_id):
        code, data = handler.handle_status(task_id)
        return jsonify(data), code

    @bp.route('/backtest/result/<task_id>')
    def backtest_result(task_id):
        code, data = handler.handle_result(task_id)
        return jsonify(data), code

    return bp
