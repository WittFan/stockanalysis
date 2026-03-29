#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mock 模块 — 在无 QMT 客户端环境下模拟 xtdata / xttrader 行为。

用途：
1. macOS 开发环境上离线开发和调试
2. 闭盘时间无实时数据时的本地测试
3. MockXtTrader 模拟下单/撤单/查询
4. MockXtData 从项目 DuckDB 读取历史行情
"""

import threading
from datetime import datetime
from types import SimpleNamespace

from loguru import logger


# ────────────────────────────────────────────────
# Mock 常量（对应 xtconstant）
# ────────────────────────────────────────────────

STOCK_BUY = 23
STOCK_SELL = 24
LATEST_PRICE = 5
FIX_PRICE = 11

ORDER_SUCCEEDED = 56
ORDER_CANCELED = 54


# ────────────────────────────────────────────────
# MockStockAccount（对应 xttype.StockAccount）
# ────────────────────────────────────────────────

class MockStockAccount:
    def __init__(self, account_id):
        self.account_id = account_id
        self.account_type = 2  # SECURITY_ACCOUNT


# ────────────────────────────────────────────────
# MockXtTrader（对应 XtQuantTrader）
# ────────────────────────────────────────────────

class MockXtTrader:
    """
    模拟 XtQuantTrader，用于离线开发和测试。
    所有操作立即返回成功，不涉及真实交易。
    """
    def __init__(self, path='', session_id=0):
        self._path = path
        self._session_id = session_id
        self._connected = False
        self._callback = None
        self._order_id_counter = 1000
        self._lock = threading.Lock()

        # 模拟状态
        self._cash = 1_000_000.0
        self._total_asset = 1_000_000.0
        self._positions = {}      # stock_code → {volume, avg_price}
        self._orders = {}         # order_id → order_info

    def register_callback(self, callback):
        self._callback = callback

    def start(self):
        logger.debug('[Mock] XtQuantTrader.start()')
        return 0

    def stop(self):
        logger.debug('[Mock] XtQuantTrader.stop()')
        self._connected = False

    def connect(self):
        self._connected = True
        logger.debug('[Mock] XtQuantTrader.connect() → 0 (成功)')
        return 0

    def subscribe(self, account):
        logger.debug(f'[Mock] subscribe({account.account_id}) → 0')
        return 0

    def unsubscribe(self, account):
        return 0

    def order_stock(self, account, stock_code, order_type, order_volume,
                    price_type, price, strategy_name='', order_remark=''):
        """模拟下单，立即返回递增的 order_id"""
        with self._lock:
            self._order_id_counter += 1
            order_id = self._order_id_counter

        direction = '买入' if order_type == STOCK_BUY else '卖出'
        logger.info(f'[Mock] 下单: {stock_code} {direction} {order_volume}股 '
                    f'@ {"最新价" if price_type == LATEST_PRICE else f"{price:.2f}"}, '
                    f'order_id={order_id}')

        # 保存订单信息
        self._orders[order_id] = {
            'stock_code': stock_code,
            'order_type': order_type,
            'order_volume': order_volume,
            'price': price,
            'order_status': ORDER_SUCCEEDED,
        }

        # 模拟更新持仓
        if order_type == STOCK_BUY:
            pos = self._positions.get(stock_code, {'volume': 0, 'avg_price': 0.0})
            pos['volume'] += order_volume
            if price > 0:
                pos['avg_price'] = price
            self._positions[stock_code] = pos
        elif order_type == STOCK_SELL:
            pos = self._positions.get(stock_code, {'volume': 0, 'avg_price': 0.0})
            pos['volume'] = max(0, pos['volume'] - order_volume)
            self._positions[stock_code] = pos

        # 异步回调（模拟成交）
        if self._callback:
            fill_price = price if price > 0 else 10.0
            xt_order = SimpleNamespace(
                account_id=account.account_id,
                stock_code=stock_code,
                order_id=order_id,
                order_type=order_type,
                order_volume=order_volume,
                price=price,
                traded_volume=order_volume,
                traded_price=fill_price,
                order_status=ORDER_SUCCEEDED,
                status_msg='模拟成交',
                strategy_name=strategy_name,
                order_remark=order_remark,
            )
            self._callback.on_stock_order(xt_order)

            xt_trade = SimpleNamespace(
                account_id=account.account_id,
                stock_code=stock_code,
                order_id=order_id,
                traded_price=fill_price,
                traded_volume=order_volume,
                traded_amount=order_volume * fill_price,
                traded_id=str(order_id),
                traded_time=int(datetime.now().timestamp()),
                strategy_name=strategy_name,
            )
            self._callback.on_stock_trade(xt_trade)

            # 持仓变动回调（更新 QMTBroker._positions）
            pos_info = self._positions.get(stock_code, {'volume': 0, 'avg_price': 0.0})
            xt_position = SimpleNamespace(
                account_id=account.account_id,
                stock_code=stock_code,
                volume=pos_info['volume'],
                can_use_volume=pos_info['volume'],
                avg_price=pos_info['avg_price'],
                open_price=pos_info['avg_price'],
                market_value=pos_info['volume'] * pos_info['avg_price'],
                frozen_volume=0,
                on_road_volume=0,
                yesterday_volume=pos_info['volume'],
            )
            self._callback.on_stock_position(xt_position)

            # 资金变动回调（简单估算）
            cost = order_volume * fill_price
            if order_type == STOCK_BUY:
                self._cash = max(0.0, self._cash - cost)
            else:
                self._cash += cost
            market_val = sum(p['volume'] * p['avg_price'] for p in self._positions.values())
            self._total_asset = self._cash + market_val
            xt_asset = SimpleNamespace(
                account_id=account.account_id,
                cash=self._cash,
                frozen_cash=0.0,
                market_value=market_val,
                total_asset=self._total_asset,
            )
            self._callback.on_stock_asset(xt_asset)

        return order_id

    def cancel_order_stock(self, account, order_id):
        logger.info(f'[Mock] 撤单: order_id={order_id}')
        if order_id in self._orders:
            self._orders[order_id]['order_status'] = ORDER_CANCELED
        return 0

    def query_stock_asset(self, account):
        """返回模拟资产"""
        return SimpleNamespace(
            account_type=2,
            account_id=account.account_id,
            cash=self._cash,
            frozen_cash=0.0,
            market_value=sum(
                p['volume'] * p['avg_price'] for p in self._positions.values()
            ),
            total_asset=self._total_asset,
        )

    def query_stock_positions(self, account):
        """返回模拟持仓列表"""
        positions = []
        for stock_code, pos in self._positions.items():
            if pos['volume'] > 0:
                positions.append(SimpleNamespace(
                    account_id=account.account_id,
                    stock_code=stock_code,
                    volume=pos['volume'],
                    can_use_volume=pos['volume'],
                    open_price=pos['avg_price'],
                    market_value=pos['volume'] * pos['avg_price'],
                    frozen_volume=0,
                    on_road_volume=0,
                    yesterday_volume=pos['volume'],
                    avg_price=pos['avg_price'],
                ))
        return positions

    def query_stock_orders(self, account, cancelable_only=False):
        """返回模拟委托列表"""
        orders = []
        for order_id, info in self._orders.items():
            orders.append(SimpleNamespace(
                account_id=account.account_id,
                stock_code=info['stock_code'],
                order_id=order_id,
                order_type=info['order_type'],
                order_volume=info['order_volume'],
                price=info['price'],
                traded_volume=info['order_volume'],
                traded_price=info['price'],
                order_status=info['order_status'],
                status_msg='',
                strategy_name='',
                order_remark='',
            ))
        return orders

    def run_forever(self):
        """阻塞主线程（mock 模式下不真正阻塞）"""
        logger.info('[Mock] run_forever() — mock 模式下立即返回')


# ────────────────────────────────────────────────
# MockXtData（对应 xtdata 模块）
# ────────────────────────────────────────────────

class MockXtData:
    """
    模拟 xtdata 模块，从项目 DuckDB 数据库读取历史行情。
    不支持实时订阅（subscribe_quote 返回 -1）。
    """

    def get_market_data(self, field_list=None, stock_list=None, period='1d',
                        start_time='', end_time='', count=-1,
                        dividend_type='none', fill_data=True):
        """
        从 DuckDB 加载历史行情，返回格式与 xtdata.get_market_data 兼容。
        返回: {field: DataFrame(index=stock_list, columns=time_list)}
        """
        import pandas as pd

        if not stock_list:
            return {}

        if field_list is None or len(field_list) == 0:
            field_list = ['open', 'high', 'low', 'close', 'volume']

        try:
            from engine.engine_utils import load_data
            df = load_data(
                symbols=stock_list,
                start_date=start_time,
                end_date=end_time,
            )

            if df is None or df.empty:
                logger.warning(f'[Mock] 未从 DuckDB 加载到数据: {stock_list}')
                return {}

            # 构造 xtdata 兼容格式
            # xtdata 返回: {field: DataFrame(index=stock_list, columns=time_list)}
            result = {}
            for field in field_list:
                if field in df.columns:
                    # df 的 index 是 date，有 symbol 列
                    pivot = df.pivot_table(
                        index='symbol', values=field, columns=df.index
                    )
                    # columns 转为字符串格式 '20230101'
                    pivot.columns = [
                        c.strftime('%Y%m%d') if hasattr(c, 'strftime') else str(c).replace('-', '')[:8]
                        for c in pivot.columns
                    ]
                    result[field] = pivot

            logger.info(f'[Mock] 从 DuckDB 加载了 {len(result.get("close", []).columns) if "close" in result else 0} 条数据')
            return result

        except Exception as e:
            logger.error(f'[Mock] 从 DuckDB 加载数据失败: {e}')
            return {}

    def subscribe_quote(self, stock_code, period='1d', callback=None, **kwargs):
        """Mock 不支持 K 线实时订阅"""
        logger.debug(f'[Mock] subscribe_quote({stock_code}, period={period}) → -1 (不支持实时)')
        return -1

    def subscribe_whole_quote(self, stock_list, callback=None, **kwargs):
        """Mock 不支持 Tick 实时订阅"""
        logger.debug(f'[Mock] subscribe_whole_quote({stock_list}) → -1 (不支持实时)')
        return -1

    def unsubscribe_quote(self, seq):
        return 0

    def download_history_data(self, stock_list, period, start_time='', end_time=''):
        """Mock 不需要下载"""
        logger.debug(f'[Mock] download_history_data: {stock_list}')
        pass

    def run(self):
        """Mock 不需要阻塞"""
        pass
