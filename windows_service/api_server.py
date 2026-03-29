#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QMT REST API 服务
=================
将 xtdata（行情）和 xttrader（交易/查询）全部接口暴露为 HTTP API，
供 Mac 端或其他客户端调用。

运行方式：
    python run_service.py          # 推荐
    python api_server.py           # 独立运行（测试）

接口分组：
  /health                         健康检查
  /api/status                     连接状态

  /api/query/asset                查询资产        ← xttrader.query_stock_asset
  /api/query/positions            查询持仓        ← xttrader.query_stock_positions
  /api/query/orders               查询当日委托    ← xttrader.query_stock_orders
  /api/query/trades               查询当日成交    ← xttrader.query_stock_trades

  /api/trade/order                下单            ← xttrader.order_stock
  /api/trade/order_async          异步下单        ← xttrader.order_stock_async
  /api/trade/cancel               撤单            ← xttrader.cancel_order_stock
  /api/trade/cancel_sysid         按合同号撤单    ← xttrader.cancel_order_stock_sysid

  /api/market/kline               K线数据         ← xtdata.get_market_data
  /api/market/tick                Tick 快照       ← xtdata.get_full_tick
  /api/market/instrument          合约基础信息    ← xtdata.get_instrument_detail
  /api/market/instrument_type     合约类型        ← xtdata.get_instrument_type
  /api/market/calendar            交易日历        ← xtdata.get_trading_dates
  /api/market/holidays            节假日列表      ← xtdata.get_holidays
  /api/market/sector              板块列表        ← xtdata.get_sector_list
  /api/market/sector/<name>       板块成分股      ← xtdata.get_stock_list_in_sector
  /api/market/index_weight        指数成分权重    ← xtdata.get_index_weight
  /api/market/divid               除权数据        ← xtdata.get_divid_factors
  /api/market/financial           财务数据        ← xtdata.get_financial_data
  /api/market/ipo                 新股申购信息    ← xtdata.get_ipo_info
"""

import hmac
import traceback
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, request
from flask_cors import CORS
from loguru import logger

import config

# =============================================================================
# Flask 应用
# =============================================================================

app = Flask(__name__)
CORS(app)

# QMTConnection 单例（由 init_store() 或 run_service.py 注入）
_store = None


def init_store():
    """
    初始化 QMT 连接（连接 MiniQMT）。
    由 run_service.py 在启动时调用；也可在 api_server.py 独立运行时自动调用。
    """
    global _store
    if _store and _store.connected:
        return True

    from qmt_connection import QMTConnection
    _store = QMTConnection(
        qmtpath=config.QMT_PATH,
        account_id=config.QMT_ACCOUNT,
        session_id=config.QMT_SESSION,
    )
    if _store.connect():
        return True
    logger.error('MiniQMT 连接失败')
    return False


def set_store(store):
    """由 run_service.py 注入已初始化的 QMTConnection"""
    global _store
    _store = store


# =============================================================================
# 工具函数
# =============================================================================

def require_auth(f):
    """Token 认证装饰器（使用 hmac.compare_digest 防止时序攻击）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if config.API_TOKEN:
            token = request.headers.get('X-API-Token', '')
            if not hmac.compare_digest(token, config.API_TOKEN):
                return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


def api_response(data=None, error=None):
    """统一响应格式"""
    if error:
        return jsonify({'success': False, 'error': error}), 500
    return jsonify({'success': True, 'data': data}), 200


def _get_trader():
    """获取 xt_trader 实例，若未就绪则返回 (None, error_msg)"""
    if _store is None:
        return None, 'QMTConnection 未初始化'
    if not _store.connected:
        return None, 'QMT 未连接'
    return _store.xt_trader, None


def _get_account():
    """获取 StockAccount 实例"""
    if _store is None:
        return None, 'QMTConnection 未初始化'
    return _store.account, None


def _get_xtdata():
    """获取 xtdata 模块"""
    try:
        from xtquant import xtdata
        return xtdata, None
    except ImportError:
        return None, 'xtquant 未安装'


# ── XtQuant 数据对象序列化 ──

def _asset_to_dict(asset):
    if asset is None:
        return None
    return {
        'account_id':   getattr(asset, 'account_id', ''),
        'cash':         getattr(asset, 'cash', 0.0),
        'frozen_cash':  getattr(asset, 'frozen_cash', 0.0),
        'market_value': getattr(asset, 'market_value', 0.0),
        'total_asset':  getattr(asset, 'total_asset', 0.0),
    }


def _position_to_dict(pos):
    if pos is None:
        return None
    return {
        'account_id':       getattr(pos, 'account_id', ''),
        'stock_code':       getattr(pos, 'stock_code', ''),
        'volume':           getattr(pos, 'volume', 0),
        'can_use_volume':   getattr(pos, 'can_use_volume', 0),
        'frozen_volume':    getattr(pos, 'frozen_volume', 0),
        'on_road_volume':   getattr(pos, 'on_road_volume', 0),
        'yesterday_volume': getattr(pos, 'yesterday_volume', 0),
        'avg_price':        getattr(pos, 'avg_price', 0.0),
        'open_price':       getattr(pos, 'open_price', 0.0),
        'market_value':     getattr(pos, 'market_value', 0.0),
    }


def _order_to_dict(order):
    if order is None:
        return None
    return {
        'account_id':    getattr(order, 'account_id', ''),
        'stock_code':    getattr(order, 'stock_code', ''),
        'order_id':      getattr(order, 'order_id', -1),
        'order_sysid':   getattr(order, 'order_sysid', ''),
        'order_type':    getattr(order, 'order_type', 0),
        'order_volume':  getattr(order, 'order_volume', 0),
        'price_type':    getattr(order, 'price_type', 0),
        'price':         getattr(order, 'price', 0.0),
        'traded_volume': getattr(order, 'traded_volume', 0),
        'traded_price':  getattr(order, 'traded_price', 0.0),
        'order_status':  getattr(order, 'order_status', 255),
        'status_msg':    getattr(order, 'status_msg', ''),
        'strategy_name': getattr(order, 'strategy_name', ''),
        'order_remark':  getattr(order, 'order_remark', ''),
    }


def _trade_to_dict(trade):
    if trade is None:
        return None
    return {
        'account_id':    getattr(trade, 'account_id', ''),
        'stock_code':    getattr(trade, 'stock_code', ''),
        'traded_id':     getattr(trade, 'traded_id', ''),
        'traded_time':   getattr(trade, 'traded_time', 0),
        'traded_price':  getattr(trade, 'traded_price', 0.0),
        'traded_volume': getattr(trade, 'traded_volume', 0),
        'traded_amount': getattr(trade, 'traded_amount', 0.0),
        'order_id':      getattr(trade, 'order_id', -1),
        'strategy_name': getattr(trade, 'strategy_name', ''),
    }


# =============================================================================
# 基础路由
# =============================================================================

@app.route('/')
def index():
    return jsonify({
        'success':   True,
        'service':   'QMT Trading Service API',
        'version':   '2.2.0',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'service': [
                'GET  /health',
                'GET  /api/status',
            ],
            'query_xttrader': [
                'GET  /api/query/asset',
                'GET  /api/query/positions',
                'GET  /api/query/orders',
                'GET  /api/query/trades',
            ],
            'trade_xttrader': [
                'POST /api/trade/order',
                'POST /api/trade/order_async',
                'POST /api/trade/cancel',
                'POST /api/trade/cancel_sysid',
            ],
            'events': [
                'GET  /api/events/orders',
                'GET  /api/events/trades',
                'GET  /api/events/errors',
                'GET  /api/events/async_responses',
            ],
            'market_xtdata': [
                'GET  /api/market/kline',
                'GET  /api/market/tick',
                'GET  /api/market/instrument',
                'GET  /api/market/instrument_type',
                'GET  /api/market/calendar',
                'GET  /api/market/holidays',
                'GET  /api/market/sector',
                'GET  /api/market/sector/<name>',
                'GET  /api/market/index_weight',
                'GET  /api/market/divid',
                'GET  /api/market/financial',
                'GET  /api/market/ipo',
            ],
        },
    })


@app.route('/health')
def health():
    """健康检查，无需认证"""
    connected = bool(_store and _store.connected)
    return jsonify({
        'status':    'healthy' if connected else 'disconnected',
        'connected': connected,
    })


@app.route('/api/status')
@require_auth
def get_status():
    """连接状态与基础配置"""
    connected = bool(_store and _store.connected)
    return api_response({
        'connected':  connected,
        'account_id': config.QMT_ACCOUNT,
        'timestamp':  datetime.now().isoformat(),
    })


# =============================================================================
# /api/query — xttrader 查询接口
# =============================================================================

@app.route('/api/query/asset')
@require_auth
def query_asset():
    """
    查询账户资产 (xttrader.query_stock_asset)
    Response: {cash, frozen_cash, market_value, total_asset}
    """
    trader, err = _get_trader()
    if err:
        return api_response(error=err)
    account, err = _get_account()
    if err:
        return api_response(error=err)
    try:
        return api_response(_asset_to_dict(trader.query_stock_asset(account)))
    except Exception as e:
        logger.error(f'query_asset: {e}')
        return api_response(error=str(e))


@app.route('/api/query/positions')
@require_auth
def query_positions():
    """
    查询持仓列表 (xttrader.query_stock_positions)
    Response: [{stock_code, volume, can_use_volume, avg_price, market_value, ...}]
    """
    trader, err = _get_trader()
    if err:
        return api_response(error=err)
    account, err = _get_account()
    if err:
        return api_response(error=err)
    try:
        positions = trader.query_stock_positions(account) or []
        return api_response([_position_to_dict(p) for p in positions])
    except Exception as e:
        logger.error(f'query_positions: {e}')
        return api_response(error=str(e))


@app.route('/api/query/orders')
@require_auth
def query_orders():
    """
    查询当日委托 (xttrader.query_stock_orders)
    ?cancelable_only=true  只返回可撤委托
    Response: [{order_id, stock_code, order_type, order_volume, price, order_status, ...}]
    """
    trader, err = _get_trader()
    if err:
        return api_response(error=err)
    account, err = _get_account()
    if err:
        return api_response(error=err)
    cancelable_only = request.args.get('cancelable_only', 'false').lower() == 'true'
    try:
        orders = trader.query_stock_orders(account, cancelable_only=cancelable_only) or []
        return api_response([_order_to_dict(o) for o in orders])
    except Exception as e:
        logger.error(f'query_orders: {e}')
        return api_response(error=str(e))


@app.route('/api/query/trades')
@require_auth
def query_trades():
    """
    查询当日成交 (xttrader.query_stock_trades)
    Response: [{stock_code, traded_price, traded_volume, traded_amount, traded_time, ...}]
    """
    trader, err = _get_trader()
    if err:
        return api_response(error=err)
    account, err = _get_account()
    if err:
        return api_response(error=err)
    try:
        trades = trader.query_stock_trades(account) or []
        return api_response([_trade_to_dict(t) for t in trades])
    except Exception as e:
        logger.error(f'query_trades: {e}')
        return api_response(error=str(e))


# =============================================================================
# /api/trade — xttrader 交易接口
# =============================================================================

@app.route('/api/trade/order', methods=['POST'])
@require_auth
def trade_order():
    """
    同步下单 (xttrader.order_stock)

    Body:
      {
        "stock_code":     "511220.SH",
        "order_type":     "buy" | "sell",
        "order_volume":   1000,
        "price_type":     "latest" | "fix",   # 默认 latest
        "price":          0.0,                # price_type=fix 时必填
        "strategy_name":  "",
        "order_remark":   ""
      }
    Response: {"success": true, "data": {"order_id": 12345}}
    """
    trader, err = _get_trader()
    if err:
        return api_response(error=err)
    account, err = _get_account()
    if err:
        return api_response(error=err)

    body         = request.get_json(silent=True) or {}
    stock_code   = body.get('stock_code', '')
    order_type   = body.get('order_type', 'buy')
    order_volume = int(body.get('order_volume', 0))
    price_type   = body.get('price_type', 'latest')
    price        = float(body.get('price', 0.0))
    strategy_name = body.get('strategy_name', '')
    order_remark  = body.get('order_remark', '')

    if not stock_code or order_volume <= 0:
        return api_response(error='stock_code 和 order_volume 必填，且 volume > 0')

    try:
        from xtquant import xtconstant
        xt_order_type = (xtconstant.STOCK_BUY if order_type == 'buy'
                         else xtconstant.STOCK_SELL)
        xt_price_type = (xtconstant.LATEST_PRICE if price_type == 'latest'
                         else xtconstant.FIX_PRICE)

        order_id = trader.order_stock(
            account, stock_code, xt_order_type,
            order_volume, xt_price_type, price,
            strategy_name, order_remark,
        )
        if order_id and order_id > 0:
            logger.info(f'下单: {stock_code} {order_type} {order_volume}股 → order_id={order_id}')
            return api_response({'order_id': order_id})
        return api_response(error=f'下单失败 (order_id={order_id})')
    except Exception as e:
        logger.error(f'trade_order: {traceback.format_exc()}')
        return api_response(error=str(e))


@app.route('/api/trade/order_async', methods=['POST'])
@require_auth
def trade_order_async():
    """
    异步下单 (xttrader.order_stock_async)
    Body: 同 /api/trade/order
    Response: {"success": true, "data": {"seq": 123}}
    """
    trader, err = _get_trader()
    if err:
        return api_response(error=err)
    account, err = _get_account()
    if err:
        return api_response(error=err)

    body          = request.get_json(silent=True) or {}
    stock_code    = body.get('stock_code', '')
    order_type    = body.get('order_type', 'buy')
    order_volume  = int(body.get('order_volume', 0))
    price_type    = body.get('price_type', 'latest')
    price         = float(body.get('price', 0.0))
    strategy_name = body.get('strategy_name', '')
    order_remark  = body.get('order_remark', '')

    if not stock_code or order_volume <= 0:
        return api_response(error='stock_code 和 order_volume 必填')

    try:
        from xtquant import xtconstant
        xt_order_type = (xtconstant.STOCK_BUY if order_type == 'buy'
                         else xtconstant.STOCK_SELL)
        xt_price_type = (xtconstant.LATEST_PRICE if price_type == 'latest'
                         else xtconstant.FIX_PRICE)

        seq = trader.order_stock_async(
            account, stock_code, xt_order_type,
            order_volume, xt_price_type, price,
            strategy_name, order_remark,
        )
        if seq and seq > 0:
            logger.info(f'异步下单: {stock_code} {order_type} {order_volume}股 → seq={seq}')
            return api_response({'seq': seq})
        return api_response(error=f'异步下单失败 (seq={seq})')
    except Exception as e:
        logger.error(f'trade_order_async: {e}')
        return api_response(error=str(e))


@app.route('/api/trade/cancel', methods=['POST'])
@require_auth
def trade_cancel():
    """
    撤单，按订单编号 (xttrader.cancel_order_stock)
    Body: {"order_id": 12345}
    Response: {"success": true, "data": {"result": 0}}
    """
    trader, err = _get_trader()
    if err:
        return api_response(error=err)
    account, err = _get_account()
    if err:
        return api_response(error=err)

    body     = request.get_json(silent=True) or {}
    order_id = body.get('order_id')
    if order_id is None:
        return api_response(error='order_id 必填')

    try:
        result = trader.cancel_order_stock(account, int(order_id))
        if result == 0:
            logger.info(f'撤单成功: order_id={order_id}')
            return api_response({'result': result})
        return api_response(error=f'撤单失败 (result={result})')
    except Exception as e:
        logger.error(f'trade_cancel: {e}')
        return api_response(error=str(e))


@app.route('/api/trade/cancel_sysid', methods=['POST'])
@require_auth
def trade_cancel_sysid():
    """
    按柜台合同编号撤单 (xttrader.cancel_order_stock_sysid)
    Body: {"market": "SH"|"SZ", "order_sysid": "T000123456"}
    """
    trader, err = _get_trader()
    if err:
        return api_response(error=err)
    account, err = _get_account()
    if err:
        return api_response(error=err)

    body        = request.get_json(silent=True) or {}
    market      = body.get('market', 'SH')
    order_sysid = body.get('order_sysid', '')
    if not order_sysid:
        return api_response(error='order_sysid 必填')

    try:
        from xtquant import xtconstant
        xt_market = (xtconstant.SH_MARKET if market.upper() == 'SH'
                     else xtconstant.SZ_MARKET)
        result = trader.cancel_order_stock_sysid(account, xt_market, order_sysid)
        return api_response({'result': result})
    except Exception as e:
        logger.error(f'trade_cancel_sysid: {e}')
        return api_response(error=str(e))


# =============================================================================
# /api/market — xtdata 行情接口
# =============================================================================

@app.route('/api/market/kline')
@require_auth
def market_kline():
    """
    K线历史数据 (xtdata.get_market_data)
    ?stocks=511220.SH,159915.SZ&period=1d&start=20240101&end=20241231
    &fields=open,high,low,close,volume&dividend_type=none&count=-1
    Response: {stock_code: {field: [v1, v2, ...]}}
    """
    xtdata, err = _get_xtdata()
    if err:
        return api_response(error=err)

    stocks        = request.args.get('stocks', '')
    period        = request.args.get('period', '1d')
    start_time    = request.args.get('start', '')
    end_time      = request.args.get('end', '')
    fields_str    = request.args.get('fields', '')
    dividend_type = request.args.get('dividend_type', 'none')
    count         = int(request.args.get('count', -1))
    fill_data     = request.args.get('fill_data', 'true').lower() == 'true'

    stock_list = [s.strip() for s in stocks.split(',') if s.strip()]
    field_list = [f.strip() for f in fields_str.split(',') if f.strip()]
    if not stock_list:
        return api_response(error='stocks 必填，如 stocks=511220.SH,159915.SZ')

    try:
        raw = xtdata.get_market_data(
            field_list=field_list, stock_list=stock_list,
            period=period, start_time=start_time, end_time=end_time,
            count=count, dividend_type=dividend_type, fill_data=fill_data,
        )
        # raw: {field: DataFrame(index=stock, columns=time)}
        # → 转为 {stock: {field: [values]}}
        result = {}
        if isinstance(raw, dict):
            for field, df in raw.items():
                if hasattr(df, 'iterrows'):
                    for stock in df.index:
                        result.setdefault(stock, {})[field] = df.loc[stock].tolist()
        return api_response(result)
    except Exception as e:
        logger.error(f'market_kline: {e}')
        return api_response(error=str(e))


@app.route('/api/market/tick')
@require_auth
def market_tick():
    """
    Tick 快照 (xtdata.get_full_tick)
    ?stocks=511220.SH,159915.SZ
    Response: {stock_code: {lastPrice, open, high, low, volume, bidPrice[5], askPrice[5], ...}}
    """
    xtdata, err = _get_xtdata()
    if err:
        return api_response(error=err)

    stocks     = request.args.get('stocks', '')
    stock_list = [s.strip() for s in stocks.split(',') if s.strip()]
    if not stock_list:
        return api_response(error='stocks 必填')

    try:
        raw    = xtdata.get_full_tick(stock_list)
        result = {}
        if isinstance(raw, dict):
            for code, data in raw.items():
                result[code] = data.tolist() if hasattr(data, 'tolist') else data
        return api_response(result)
    except Exception as e:
        logger.error(f'market_tick: {e}')
        return api_response(error=str(e))


@app.route('/api/market/instrument')
@require_auth
def market_instrument():
    """
    合约基础信息 (xtdata.get_instrument_detail)
    ?stock=511220.SH
    Response: {InstrumentName, PreClose, UpStopPrice, DownStopPrice, FloatVolume, ...}
    """
    xtdata, err = _get_xtdata()
    if err:
        return api_response(error=err)

    stock = request.args.get('stock', '')
    if not stock:
        return api_response(error='stock 必填')

    try:
        detail = xtdata.get_instrument_detail(stock)
        if detail is None:
            return api_response(error=f'{stock} 合约信息未找到')
        if isinstance(detail, dict):
            return api_response(detail)
        return api_response({k: getattr(detail, k)
                             for k in dir(detail) if not k.startswith('_')})
    except Exception as e:
        logger.error(f'market_instrument: {e}')
        return api_response(error=str(e))


@app.route('/api/market/instrument_type')
@require_auth
def market_instrument_type():
    """
    合约类型 (xtdata.get_instrument_type)
    ?stock=511220.SH
    Response: {"stock": "511220.SH", "type": "etf"}
    """
    xtdata, err = _get_xtdata()
    if err:
        return api_response(error=err)

    stock = request.args.get('stock', '')
    if not stock:
        return api_response(error='stock 必填')

    try:
        itype = xtdata.get_instrument_type(stock)
        return api_response({'stock': stock, 'type': itype})
    except Exception as e:
        logger.error(f'market_instrument_type: {e}')
        return api_response(error=str(e))


@app.route('/api/market/calendar')
@require_auth
def market_calendar():
    """
    交易日历 (xtdata.get_trading_dates)
    ?market=SH&start=20240101&end=20241231
    Response: ["20240102", "20240103", ...]
    """
    xtdata, err = _get_xtdata()
    if err:
        return api_response(error=err)

    market     = request.args.get('market', 'SH')
    start_time = request.args.get('start', '')
    end_time   = request.args.get('end', '')
    count      = int(request.args.get('count', -1))

    try:
        from datetime import datetime, timezone
        dates = xtdata.get_trading_dates(market, start_time=start_time,
                                         end_time=end_time, count=count)
        def _to_date_str(d):
            if isinstance(d, str):
                return d  # 已经是字符串（如 "20240102"）
            # xtdata 返回毫秒时间戳整数，转为 YYYYMMDD
            return datetime.fromtimestamp(int(d) / 1000, tz=timezone.utc).strftime('%Y%m%d')
        date_list = [_to_date_str(d) for d in (dates or [])]
        return api_response(date_list)
    except Exception as e:
        logger.error(f'market_calendar: {e}')
        return api_response(error=str(e))


@app.route('/api/market/holidays')
@require_auth
def market_holidays():
    """
    节假日列表 (xtdata.get_holidays)
    Response: ["20240101", ...]
    """
    xtdata, err = _get_xtdata()
    if err:
        return api_response(error=err)
    try:
        holidays = xtdata.get_holidays()
        return api_response(list(holidays) if holidays else [])
    except Exception as e:
        logger.error(f'market_holidays: {e}')
        return api_response(error=str(e))


@app.route('/api/market/sector')
@require_auth
def market_sector_list():
    """
    板块列表 (xtdata.get_sector_list)
    Response: ["沪深300", "中证500", ...]
    """
    xtdata, err = _get_xtdata()
    if err:
        return api_response(error=err)
    try:
        sectors = xtdata.get_sector_list()
        return api_response(list(sectors) if sectors else [])
    except Exception as e:
        logger.error(f'market_sector_list: {e}')
        return api_response(error=str(e))


@app.route('/api/market/sector/<path:sector_name>')
@require_auth
def market_sector_stocks(sector_name):
    """
    板块成分股 (xtdata.get_stock_list_in_sector)
    GET /api/market/sector/沪深300
    Response: ["000001.SZ", "600000.SH", ...]
    """
    xtdata, err = _get_xtdata()
    if err:
        return api_response(error=err)
    try:
        stocks = xtdata.get_stock_list_in_sector(sector_name)
        return api_response(list(stocks) if stocks else [])
    except Exception as e:
        logger.error(f'market_sector_stocks: {e}')
        return api_response(error=str(e))


@app.route('/api/market/index_weight')
@require_auth
def market_index_weight():
    """
    指数成分股权重 (xtdata.get_index_weight)
    ?index=000300.SH
    Response: {"000001.SZ": 0.0123, ...}
    """
    xtdata, err = _get_xtdata()
    if err:
        return api_response(error=err)

    index_code = request.args.get('index', '')
    if not index_code:
        return api_response(error='index 必填，如 index=000300.SH')

    try:
        weights = xtdata.get_index_weight(index_code)
        if weights is None:
            return api_response({})
        return api_response(weights.to_dict() if hasattr(weights, 'to_dict')
                            else dict(weights))
    except Exception as e:
        logger.error(f'market_index_weight: {e}')
        return api_response(error=str(e))


@app.route('/api/market/divid')
@require_auth
def market_divid():
    """
    除权数据 (xtdata.get_divid_factors)
    ?stock=600000.SH&start=20200101&end=20241231
    Response: [{interest, stockBonus, stockGift, ...}, ...]
    """
    xtdata, err = _get_xtdata()
    if err:
        return api_response(error=err)

    stock      = request.args.get('stock', '')
    start_time = request.args.get('start', '')
    end_time   = request.args.get('end', '')
    if not stock:
        return api_response(error='stock 必填')

    try:
        df = xtdata.get_divid_factors(stock, start_time=start_time, end_time=end_time)
        if df is None:
            return api_response([])
        return api_response(df.to_dict(orient='records')
                            if hasattr(df, 'to_dict') else [])
    except Exception as e:
        logger.error(f'market_divid: {e}')
        return api_response(error=str(e))


@app.route('/api/market/financial')
@require_auth
def market_financial():
    """
    财务数据 (xtdata.get_financial_data)
    ?stocks=600000.SH,000001.SZ&tables=Income,Balance
    &start=20200101&end=20241231&report_type=report_time
    Response: {table: [records...]}
    """
    xtdata, err = _get_xtdata()
    if err:
        return api_response(error=err)

    stocks_str  = request.args.get('stocks', '')
    tables_str  = request.args.get('tables', '')
    start_time  = request.args.get('start', '')
    end_time    = request.args.get('end', '')
    report_type = request.args.get('report_type', 'report_time')

    stock_list = [s.strip() for s in stocks_str.split(',') if s.strip()]
    table_list = [t.strip() for t in tables_str.split(',') if t.strip()]
    if not stock_list:
        return api_response(error='stocks 必填')

    try:
        raw = xtdata.get_financial_data(
            stock_list, table_list=table_list,
            start_time=start_time, end_time=end_time,
            report_type=report_type,
        )
        if raw is None:
            return api_response({})
        result = {table: (df.to_dict(orient='records')
                          if hasattr(df, 'to_dict') else [])
                  for table, df in raw.items()} if isinstance(raw, dict) else {}
        return api_response(result)
    except Exception as e:
        logger.error(f'market_financial: {e}')
        return api_response(error=str(e))


@app.route('/api/market/ipo')
@require_auth
def market_ipo():
    """
    新股申购信息 (xtdata.get_ipo_info)
    ?start=20240101&end=20241231
    Response: [{stock_code, ipo_date, ...}, ...]
    """
    xtdata, err = _get_xtdata()
    if err:
        return api_response(error=err)

    start_time = request.args.get('start', '')
    end_time   = request.args.get('end', '')

    try:
        raw = xtdata.get_ipo_info(start_time, end_time)
        if raw is None:
            return api_response([])
        if hasattr(raw, 'to_dict'):
            return api_response(raw.to_dict(orient='records'))
        return api_response(raw if isinstance(raw, list) else [])
    except Exception as e:
        logger.error(f'market_ipo: {e}')
        return api_response(error=str(e))


# =============================================================================
# =============================================================================
# /api/events — 回调事件消费接口（Mac 端轮询）
# =============================================================================

def _drain_queue(q, limit: int) -> list:
    """从队列中取出最多 limit 条，非阻塞"""
    import queue
    items = []
    for _ in range(limit):
        try:
            items.append(q.get_nowait())
        except queue.Empty:
            break
    return items


@app.route('/api/events/orders')
@require_auth
def events_orders():
    """
    消费委托推送事件（on_stock_order）
    ?limit=50  每次最多取条数（默认 50）
    Response: [{"order_id":…, "stock_code":…, "order_status":…, "status_msg":…, …}]
    """
    if _store is None or getattr(_store, 'callback', None) is None:
        return api_response([])
    limit = int(request.args.get('limit', 50))
    return api_response(_drain_queue(_store.callback.orders, limit))


@app.route('/api/events/trades')
@require_auth
def events_trades():
    """
    消费成交推送事件（on_stock_trade）
    ?limit=50
    Response: [{"order_id":…, "stock_code":…, "traded_volume":…, "traded_price":…, …}]
    """
    if _store is None or getattr(_store, 'callback', None) is None:
        return api_response([])
    limit = int(request.args.get('limit', 50))
    return api_response(_drain_queue(_store.callback.trades, limit))


@app.route('/api/events/errors')
@require_auth
def events_errors():
    """
    消费错误推送事件（on_order_error / on_cancel_error）
    ?limit=50
    Response: [{"type":"order_error"|"cancel_error", "order_id":…, "error_id":…, "error_msg":…}]
    """
    if _store is None or getattr(_store, 'callback', None) is None:
        return api_response([])
    limit = int(request.args.get('limit', 50))
    return api_response(_drain_queue(_store.callback.errors, limit))


@app.route('/api/events/async_responses')
@require_auth
def events_async_responses():
    """
    消费异步下单/撤单响应（on_order_stock_async_response）
    ?limit=50
    Response: [{"type":"order_async"|"cancel_async", "seq":…, "order_id":…, "error_id":…}]
    """
    if _store is None or getattr(_store, 'callback', None) is None:
        return api_response([])
    limit = int(request.args.get('limit', 50))
    return api_response(_drain_queue(_store.callback.async_responses, limit))


# =============================================================================
# 启动函数
# =============================================================================

def start_api_server(store=None, host=None, port=None, debug=False):
    """
    启动 API 服务器（非阻塞，在后台线程中运行）

    Args:
        store: 已初始化的 QMTConnection 实例（由 run_service.py 传入）
        host:  监听地址（默认 config.API_HOST）
        port:  监听端口（默认 config.API_PORT）
    """
    if store is not None:
        set_store(store)

    host = host or config.API_HOST
    port = port or config.API_PORT

    import threading

    def _run():
        try:
            app.run(host=host, port=port, debug=debug, use_reloader=False)
        except Exception as e:
            logger.error(f'Flask 启动失败（端口 {port} 可能已被占用）: {e}')

    t = threading.Thread(target=_run, daemon=True, name='api-server')
    t.start()
    logger.info(f'QMT API 已启动: http://{host}:{port}')
    return t


def main():
    """独立运行（测试用）：自动初始化 QMTConnection 并启动 API"""
    if not init_store():
        logger.error('连接失败，退出')
        return

    start_api_server()

    try:
        import time
        logger.info('API 运行中，按 Ctrl+C 停止')
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info('停止')


if __name__ == '__main__':
    main()
