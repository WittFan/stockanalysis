#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QMTBroker — Backtrader Broker 层，管理 QMT 订单与持仓。

职责：
1. 实现 BrokerBase 接口（getcash/getvalue/getposition/submit/cancel/next）
2. 将 Backtrader Order 映射为 QMT order_stock 调用
3. 处理 QMTStore 转发的委托/成交/资金/持仓回调
"""

from copy import copy
from datetime import datetime

from loguru import logger

from backtrader import BrokerBase, Order, Position, CommInfoBase
from backtrader.order import BuyOrder, SellOrder
from backtrader.utils.py3 import queue


class QMTBroker(BrokerBase):
    """
    Backtrader Broker 实现，通过 QMTStore 与 QMT 客户端交互。

    用法::

        store = QMTStore(...)
        broker = store.getbroker()
        cerebro.setbroker(broker)
    """

    params = (
        ('use_positions', True),    # 启动时是否同步 QMT 持仓
        ('strategy_name', 'bt'),    # QMT 策略名称标记
    )

    # QMT 委托状态 → Backtrader Order 状态映射
    _ORDER_STATUS_MAP = {
        48: None,                   # ORDER_UNREPORTED — 未报，忽略
        49: None,                   # ORDER_WAIT_REPORTING — 待报，忽略
        50: Order.Accepted,         # ORDER_REPORTED — 已报
        51: Order.Accepted,         # ORDER_REPORTED_CANCEL — 已报待撤
        52: Order.Partial,          # ORDER_PARTSUCC_CANCEL — 部成待撤
        53: Order.Cancelled,        # ORDER_PART_CANCEL — 部撤
        54: Order.Cancelled,        # ORDER_CANCELED — 已撤
        55: Order.Partial,          # ORDER_PART_SUCC — 部成
        56: Order.Completed,        # ORDER_SUCCEEDED — 已成
        57: Order.Rejected,         # ORDER_JUNK — 废单
    }

    def __init__(self, **kwargs):
        super().__init__()

        self.store = kwargs.pop('store')
        self.store._broker = self

        # 订单映射
        self._orders = {}           # bt_order_ref → Order
        self._qmt2bt = {}           # qmt_order_id → bt_order_ref
        self._bt2qmt = {}           # bt_order_ref → qmt_order_id

        # 持仓
        self._positions = {}        # stock_code → Position

        # 资金
        self._cash = 0.0
        self._value = 0.0

        # Backtrader 约定：startingcash / startingvalue（Cerebro Writer 需要）
        self.startingcash = 0.0
        self.startingvalue = 0.0

        # 待处理事件队列（从回调线程安全传递到 next() 主线程）
        self._event_queue = queue.Queue()

        # 通知存储
        self.notifs = queue.Queue()

    # ────────── BrokerBase 必须实现的工厂方法 ──────────

    def getcommissioninfo(self, data):
        """返回默认零佣金（实盘可扩展为按标的类型设置费率）"""
        return CommInfoBase()

    def buy(self, owner, data, size, price=None, plimit=None,
            exectype=None, valid=None, tradeid=0, oco=None,
            trailamount=None, trailpercent=None,
            parent=None, transmit=True, **kwargs):
        """由 Strategy.buy() 调用，创建买入订单并提交"""
        order = BuyOrder(
            owner=owner, data=data,
            size=size, price=price, pricelimit=plimit,
            exectype=exectype, valid=valid, tradeid=tradeid,
            trailamount=trailamount, trailpercent=trailpercent,
        )
        order.addcomminfo(self.getcommissioninfo(data))
        return self.submit(order)

    def sell(self, owner, data, size, price=None, plimit=None,
             exectype=None, valid=None, tradeid=0, oco=None,
             trailamount=None, trailpercent=None,
             parent=None, transmit=True, **kwargs):
        """由 Strategy.sell() 调用，创建卖出订单并提交"""
        order = SellOrder(
            owner=owner, data=data,
            size=size, price=price, pricelimit=plimit,
            exectype=exectype, valid=valid, tradeid=tradeid,
            trailamount=trailamount, trailpercent=trailpercent,
        )
        order.addcomminfo(self.getcommissioninfo(data))
        return self.submit(order)

    def start(self):
        """Broker 启动，向 Store 注册并同步初始状态"""
        super().start()
        self.store.start(broker=self)

        if self.p.use_positions and self.store.connected:
            self._sync_positions()
            self._sync_asset()
            self.startingcash  = self._cash
            self.startingvalue = self._value

    def stop(self):
        super().stop()

    # ────────── BrokerBase 必须实现的接口 ──────────

    def getcash(self):
        return self._cash

    def getvalue(self, datas=None):
        return self._value

    def getposition(self, data, clone=True):
        """返回指定 data 的持仓"""
        stock_code = data.p.dataname if hasattr(data.p, 'dataname') else str(data)
        pos = self._positions.get(stock_code, Position())
        if clone:
            return pos.clone()
        return pos

    def submit(self, order):
        """
        提交订单到 QMT。
        将 Backtrader Order 转换为 QMT order_stock 调用。
        """
        order.submit(self)
        self._orders[order.ref] = order
        self.notify(order)

        # 提取订单参数
        data = order.data
        stock_code = data.p.dataname
        size = abs(int(order.created.size))

        # 映射买卖方向
        if order.isbuy():
            order_type = self._get_constant('STOCK_BUY')
        else:
            order_type = self._get_constant('STOCK_SELL')

        # 映射价格类型
        price = order.created.price or 0.0
        if order.exectype == Order.Market:
            price_type = self._get_constant('LATEST_PRICE')
            price = 0.0  # 最新价不需要指定价格
        elif order.exectype == Order.Limit:
            price_type = self._get_constant('FIX_PRICE')
        else:
            # 其他类型默认用最新价
            price_type = self._get_constant('LATEST_PRICE')
            price = 0.0

        # 下单
        try:
            qmt_order_id = self.store.xt_trader.order_stock(
                self.store.account,
                stock_code,
                order_type,
                size,
                price_type,
                price,
                self.p.strategy_name,
                f'bt_ref_{order.ref}',
            )

            if qmt_order_id and qmt_order_id > 0:
                self._qmt2bt[qmt_order_id] = order.ref
                self._bt2qmt[order.ref] = qmt_order_id
                order.accept(self)
                self.notify(order)
                logger.info(f'下单成功: {stock_code} {"买入" if order.isbuy() else "卖出"} '
                            f'{size}股, qmt_id={qmt_order_id}')
            else:
                order.reject(self)
                self.notify(order)
                logger.warning(f'下单失败: {stock_code}, 返回 order_id={qmt_order_id}')

        except Exception as e:
            order.reject(self)
            self.notify(order)
            logger.error(f'下单异常: {stock_code}, {e}')

        return order

    def cancel(self, order):
        """撤销订单"""
        qmt_order_id = self._bt2qmt.get(order.ref)
        if qmt_order_id is None:
            logger.warning(f'撤单失败: 找不到 bt_ref={order.ref} 对应的 QMT 订单')
            return

        try:
            result = self.store.xt_trader.cancel_order_stock(
                self.store.account, qmt_order_id
            )
            if result == 0:
                logger.info(f'撤单请求已发送: qmt_id={qmt_order_id}')
            else:
                logger.warning(f'撤单请求失败: qmt_id={qmt_order_id}, code={result}')
        except Exception as e:
            logger.error(f'撤单异常: {e}')

    def next(self):
        """
        每根 bar 调用。处理事件队列中的回调事件。
        在 live 模式下由 Cerebro 主循环调用。
        """
        while True:
            try:
                event_type, event_data = self._event_queue.get(block=False)
            except queue.Empty:
                break

            if event_type == 'order':
                self._handle_order_event(event_data)
            elif event_type == 'trade':
                self._handle_trade_event(event_data)
            elif event_type == 'asset':
                self._handle_asset_event(event_data)
            elif event_type == 'position':
                self._handle_position_event(event_data)
            elif event_type == 'order_error':
                self._handle_order_error_event(event_data)

    # ────────── Store 回调转发入口（从回调线程调用） ──────────

    def _process_order_event(self, xt_order):
        """委托状态变动（由 Store 回调线程调用）"""
        self._event_queue.put(('order', xt_order))

    def _process_trade_event(self, xt_trade):
        """成交回报（由 Store 回调线程调用）"""
        self._event_queue.put(('trade', xt_trade))

    def _update_asset_from_event(self, xt_asset):
        """资金变动（由 Store 回调线程调用）"""
        self._event_queue.put(('asset', xt_asset))

    def _update_position_from_event(self, xt_position):
        """持仓变动（由 Store 回调线程调用）"""
        self._event_queue.put(('position', xt_position))

    def _process_order_error(self, xt_error):
        """下单错误（由 Store 回调线程调用）"""
        self._event_queue.put(('order_error', xt_error))

    # ────────── 事件处理（在主线程 next() 中执行） ──────────

    def _handle_order_event(self, xt_order):
        """处理委托状态变动"""
        qmt_id = getattr(xt_order, 'order_id', None)
        bt_ref = self._qmt2bt.get(qmt_id)

        if bt_ref is None:
            # 可能是非本策略的订单
            logger.debug(f'收到未知订单回报: qmt_id={qmt_id}, stock={getattr(xt_order, "stock_code", "?")}')
            return

        order = self._orders.get(bt_ref)
        if order is None:
            return

        status = getattr(xt_order, 'order_status', None)
        bt_status = self._ORDER_STATUS_MAP.get(status)

        if bt_status is None:
            return  # 忽略中间态

        traded_volume = getattr(xt_order, 'traded_volume', 0)
        traded_price = getattr(xt_order, 'traded_price', 0.0)

        if bt_status == Order.Completed:
            order.completed()
            logger.info(f'订单完成: {xt_order.stock_code}, '
                        f'成交 {traded_volume}股 @ {traded_price}')
        elif bt_status == Order.Partial:
            order.partial()
            logger.info(f'订单部分成交: {xt_order.stock_code}, '
                        f'已成交 {traded_volume}股 @ {traded_price}')
        elif bt_status == Order.Cancelled:
            order.cancel()
            logger.info(f'订单已撤: {xt_order.stock_code}')
        elif bt_status == Order.Rejected:
            order.reject(self)
            msg = getattr(xt_order, 'status_msg', '')
            logger.warning(f'订单废单: {xt_order.stock_code}, {msg}')

        self.notify(order)

    def _handle_trade_event(self, xt_trade):
        """处理成交回报"""
        qmt_id = getattr(xt_trade, 'order_id', None)
        bt_ref = self._qmt2bt.get(qmt_id)

        if bt_ref is None:
            return

        order = self._orders.get(bt_ref)
        if order is None:
            return

        traded_price = getattr(xt_trade, 'traded_price', 0.0)
        traded_volume = getattr(xt_trade, 'traded_volume', 0)

        # 更新 order.executed
        order.execute(
            dt=datetime.now(),
            size=traded_volume if order.isbuy() else -traded_volume,
            price=traded_price,
            closed=0,
            closedvalue=0.0,
            closedcomm=0.0,
            opened=traded_volume,
            openedvalue=traded_price * traded_volume,
            openedcomm=0.0,
            margin=0.0,
            pnl=0.0,
            psize=0,
            pprice=0.0,
        )

        logger.debug(f'成交: {xt_trade.stock_code}, '
                      f'{traded_volume}股 @ {traded_price}')

    def _handle_asset_event(self, xt_asset):
        """处理资金变动"""
        self._cash = getattr(xt_asset, 'cash', self._cash)
        self._value = getattr(xt_asset, 'total_asset', self._value)

    def _handle_position_event(self, xt_position):
        """处理持仓变动"""
        stock_code = getattr(xt_position, 'stock_code', None)
        if stock_code is None:
            return

        volume = getattr(xt_position, 'volume', 0)
        avg_price = getattr(xt_position, 'avg_price', 0.0)

        pos = self._positions.get(stock_code)
        if pos is None:
            pos = Position()
            self._positions[stock_code] = pos

        # 同步持仓（简化处理：直接设置）
        pos.size = volume
        pos.price = avg_price

    def _handle_order_error_event(self, xt_error):
        """处理下单错误"""
        qmt_id = getattr(xt_error, 'order_id', None)
        bt_ref = self._qmt2bt.get(qmt_id)

        if bt_ref is None:
            logger.warning(f'下单错误(未知订单): error={getattr(xt_error, "error_msg", "?")}')
            return

        order = self._orders.get(bt_ref)
        if order:
            order.reject(self)
            self.notify(order)
            logger.warning(f'下单错误: qmt_id={qmt_id}, '
                           f'{getattr(xt_error, "error_msg", "")}')

    # ────────── 辅助方法 ──────────

    def _sync_positions(self):
        """从 QMT 同步当前持仓"""
        try:
            positions = self.store.xt_trader.query_stock_positions(self.store.account)
            if positions:
                for p in positions:
                    stock_code = p.stock_code
                    pos = Position()
                    pos.size = p.volume
                    pos.price = p.avg_price
                    self._positions[stock_code] = pos
                logger.info(f'同步持仓完成: {len(positions)} 只标的')
            else:
                logger.info('当前无持仓')
        except Exception as e:
            logger.error(f'同步持仓异常: {e}')

    def _sync_asset(self):
        """从 QMT 同步资金信息"""
        try:
            asset = self.store.xt_trader.query_stock_asset(self.store.account)
            if asset:
                self._cash = asset.cash
                self._value = asset.total_asset
                logger.info(f'同步资金完成: 可用={self._cash:.2f}, 总资产={self._value:.2f}')
        except Exception as e:
            logger.error(f'同步资金异常: {e}')

    def _get_constant(self, name):
        """获取 xtconstant 常量，mock 模式下返回整数"""
        try:
            from xtquant import xtconstant
            return getattr(xtconstant, name)
        except ImportError:
            # mock 模式下的常量映射
            _MOCK_CONSTANTS = {
                'STOCK_BUY': 23,
                'STOCK_SELL': 24,
                'LATEST_PRICE': 5,
                'FIX_PRICE': 11,
            }
            return _MOCK_CONSTANTS.get(name, 0)

    def notify(self, order):
        self.notifs.put(order.clone())

    def get_notification(self):
        try:
            return self.notifs.get(block=False)
        except queue.Empty:
            return None
