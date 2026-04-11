from flask import Blueprint, jsonify, request


def make_value_bp(handler) -> Blueprint:
    bp = Blueprint('value', __name__)

    @bp.route('/value/data')
    def value_data():
        # 兼容 handler 原有的 {key: [val]} 格式
        qs = {k: [v] for k, v in request.args.items()}
        code, data = handler.handle_data_api(qs)
        return jsonify(data), code

    @bp.route('/value/forecast', methods=['POST'])
    def value_forecast():
        code, data = handler.handle_forecast(request.get_data())
        return jsonify(data), code

    return bp
