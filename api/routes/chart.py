from flask import Blueprint, jsonify, request


def _parse_period(val, default=3):
    try:
        p = int(val)
        return max(1, min(3, p))
    except (ValueError, TypeError):
        return default


def make_chart_bp(handler) -> Blueprint:
    bp = Blueprint('chart', __name__)

    @bp.route('/chart')
    def chart():
        period = _parse_period(request.args.get('period', 3))
        return jsonify(handler.handle_chart(period))

    @bp.route('/industry')
    def industry():
        period = _parse_period(request.args.get('period', 3))
        return jsonify(handler.handle_industry(period))

    return bp
