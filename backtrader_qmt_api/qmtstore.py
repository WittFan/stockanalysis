#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QMTStore — Backtrader Store 层，管理与 QMT (MiniQMT) 的连接。

职责：
1. 维护 XtQuantTrader 连接（MetaSingleton 单例）
2. 实现 XtQuantTraderCallback 回调，转发给 Broker
3. 提供 getdata() / getbroker() 工厂方法
"""

import collections
import threading
import time
import random

from loguru import logger

from backtrader.metabase import MetaParams
from backtrader.utils.py3 import queue, with_metaclass

# ────────────────────────────────────────────────
# MetaSingleton：保证 QMTStore 全局唯一
# ────────────────────────────────────────────────

class MetaSingleton(MetaParams):
    """元类：确保 QMTStore 只有一个实例"""
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        cls._singleton = None

    def __call__(cls, *args, **kwargs):
        if cls._singleton is None:
            cls._singleton = super().__call__(*args, **kwargs)
        return cls._singleton


# ────────────────────────────────────────────────
# QMTStore
# ────────────────────────────────────────────────

class QMTStore(with_metaclass(MetaSingleton, object)):
    """
    Backtrader Store 实现，封装 QMT 连接管理。

    用法::

        store = QMTStore(qmtpath=r'D:\\...\\userdata_mini',
                         account_id='1000000365')
        broker = store.getbroker()
        data   = store.getdata(dataname='511220.SH')
    """

    # --- Backtrader Store 约定：关联的 Broker / Data 类 ---
    BrokerCls = None    # 由 QMTBroker 模块自动赋值
    DataCls = None      # 由 QMTData 模块自动赋值

    params = (
        ('qmtpath', ''),           # MiniQMT userdata_mini 路径
        ('account_id', ''),        # 资金账号
        ('session_id', 0),         # 会话ID，0 则随机生成
        ('reconnect', 3),          # 最大重连次数
        ('timeout', 10.0),         # 连接超时（秒）
        ('use_mock', False),       # 是否使用 mock 模式（离线开发）
    )

    def __init__(self):
        super().__init__()

        self.notifs = queue.Queue()       # 通知队列
        self._lock = threading.Lock()

        # 连接状态
        self.connected = False
        self._broker = None               # 关联的 QMTBroker 实例
        self._datas = []                   # 关联的 QMTData 实例列表

        # QMT 核心对象（connect 后赋值）
        self.xt_trader = None
        self.account = None

        # 从 setting.py 读取默认配置（如果 params 未指定）
        if not self.p.qmtpath or not self.p.account_id:
            self._load_default_settings()

        # 确定 session_id
        if self.p.session_id == 0:
            self.p.session_id = random.randint(100000, 999999)

    def _load_default_settings(self):
        """从项目 setting.py 中加载默认配置"""
        try:
            from setting import qmtpath, qmtaccount, session_id
            if not self.p.qmtpath:
                self.p.qmtpath = qmtpath
            if not self.p.account_id:
                self.p.account_id = qmtaccount
            if self.p.session_id == 0:
                self.p.session_id = session_id
        except ImportError:
            logger.warning('setting.py 未找到，请手动传入 qmtpath 和 account_id')

    # ────────── 连接管理 ──────────

    def start(self, data=None, broker=None):
        """
        Backtrader Store 约定的 start 方法。
        由 Cerebro 启动时调用；data/broker 注册自身。
        """
        if data is not None:
            self._datas.append(data)

        if broker is not None:
            self._broker = broker

        # 首次调用时建立连接
        if not self.connected:
            self.connect()

    def stop(self):
        """断开连接"""
        if self.xt_trader is not None:
            try:
                self.xt_trader.stop()
            except Exception as e:
                logger.warning(f'停止 XtQuantTrader 异常: {e}')
        self.connected = False
        logger.info('QMTStore 已停止')

    def connect(self):
        """
        连接 MiniQMT 客户端。
        mock 模式下使用 MockXtTrader。
        """
        if self.connected:
            return True

        if self.p.use_mock:
            return self._connect_mock()

        return self._connect_real()

    def _connect_real(self):
        """真实连接 QMT"""
        try:
            from xtquant.xttrader import XtQuantTrader
            from xtquant.xttype import StockAccount
        except ImportError:
            logger.error('xtquant 未安装，无法连接 QMT。请使用 use_mock=True 进行离线开发')
            return False

        for attempt in range(1, self.p.reconnect + 1):
            logger.info(f'正在连接 MiniQMT (第 {attempt}/{self.p.reconnect} 次)...')
            try:
                self.xt_trader = XtQuantTrader(self.p.qmtpath, self.p.session_id)

                # 注册回调
                callback = _QMTCallback(self)
                self.xt_trader.register_callback(callback)

                self.xt_trader.start()
                result = self.xt_trader.connect()

                if result == 0:
                    # 创建账号并订阅
                    self.account = StockAccount(self.p.account_id)
                    sub_result = self.xt_trader.subscribe(self.account)
                    if sub_result == 0:
                        self.connected = True
                        logger.info(f'MiniQMT 连接成功，账号: {self.p.account_id}')
                        return True
                    else:
                        logger.warning(f'账号订阅失败 (code={sub_result})')
                else:
                    logger.warning(f'MiniQMT 连接失败 (code={result})')

            except Exception as e:
                logger.error(f'连接异常: {e}')

            if attempt < self.p.reconnect:
                time.sleep(2)

        logger.error('MiniQMT 连接失败，已达最大重试次数')
        return False

    def _connect_mock(self):
        """使用 Mock 模式连接"""
        from .mock import MockXtTrader, MockStockAccount
        self.xt_trader = MockXtTrader(self.p.qmtpath, self.p.session_id)
        # 注册回调（与真实连接保持一致，事件链：MockXtTrader → _QMTCallback → QMTStore → QMTBroker）
        callback = _QMTCallback(self)
        self.xt_trader.register_callback(callback)
        self.xt_trader.start()
        self.xt_trader.connect()
        self.account = MockStockAccount(self.p.account_id)
        self.xt_trader.subscribe(self.account)
        self.connected = True
        logger.info(f'QMTStore Mock 模式已启动，账号: {self.p.account_id}')
        return True

    # ────────── 工厂方法 ──────────

    def getbroker(self, **kwargs):
        """创建并返回 QMTBroker 实例"""
        if self.BrokerCls is None:
            from .qmtbroker import QMTBroker
            self.BrokerCls = QMTBroker
        return self.BrokerCls(store=self, **kwargs)

    def getdata(self, **kwargs):
        """创建并返回 QMTData 实例"""
        if self.DataCls is None:
            from .qmtdata import QMTData
            self.DataCls = QMTData
        return self.DataCls(store=self, **kwargs)

    # ────────── 通知机制 ──────────

    def put_notification(self, msg, *args, **kwargs):
        self.notifs.put((msg, args, kwargs))

    def get_notifications(self):
        """yield 所有待处理通知"""
        while True:
            try:
                msg, args, kwargs = self.notifs.get(block=False)
                yield msg, args, kwargs
            except queue.Empty:
                break

    # ────────── Broker 回调转发 ──────────

    def _on_order_event(self, xt_order):
        """委托状态变动，转发给 Broker"""
        if self._broker:
            self._broker._process_order_event(xt_order)

    def _on_trade_event(self, xt_trade):
        """成交回报，转发给 Broker"""
        if self._broker:
            self._broker._process_trade_event(xt_trade)

    def _on_asset_event(self, xt_asset):
        """资金变动，转发给 Broker"""
        if self._broker:
            self._broker._update_asset_from_event(xt_asset)

    def _on_position_event(self, xt_position):
        """持仓变动，转发给 Broker"""
        if self._broker:
            self._broker._update_position_from_event(xt_position)

    def _on_order_error(self, xt_error):
        """下单错误，转发给 Broker"""
        if self._broker:
            self._broker._process_order_error(xt_error)

    def _on_cancel_error(self, xt_error):
        """撤单错误"""
        logger.warning(f'撤单失败: order_id={xt_error.order_id}, '
                       f'error={xt_error.error_id}: {xt_error.error_msg}')
        self.put_notification(f'撤单失败: {xt_error.error_msg}')

    def _on_disconnected(self):
        """断开连接回调"""
        self.connected = False
        self.put_notification('QMT 连接已断开')
        logger.warning('QMT 连接已断开')


# ────────────────────────────────────────────────
# XtQuantTraderCallback 实现
# ────────────────────────────────────────────────

# 在 Windows/xtquant 环境下，register_callback() 要求传入
# XtQuantTraderCallback 的子类实例；非 Windows 开发环境回退到 object。
try:
    from xtquant.xttrader import XtQuantTraderCallback as _CallbackBase
except ImportError:
    _CallbackBase = object


class _QMTCallback(_CallbackBase):
    """
    QMT 回调代理。
    将 XtQuantTraderCallback 的各回调方法转发给 QMTStore。

    继承策略：
    - Windows (xtquant 可用)：继承 XtQuantTraderCallback，满足 register_callback 要求
    - macOS/Linux (开发环境)：继承 object，用于 mock 测试
    """
    def __init__(self, store):
        if _CallbackBase is not object:
            super().__init__()
        self._store = store

    def on_disconnected(self):
        self._store._on_disconnected()

    def on_stock_order(self, order):
        self._store._on_order_event(order)

    def on_stock_trade(self, trade):
        self._store._on_trade_event(trade)

    def on_stock_asset(self, asset):
        self._store._on_asset_event(asset)

    def on_stock_position(self, position):
        self._store._on_position_event(position)

    def on_order_error(self, order_error):
        self._store._on_order_error(order_error)

    def on_cancel_error(self, cancel_error):
        self._store._on_cancel_error(cancel_error)

    def on_account_status(self, status):
        logger.debug(f'账号状态变动: {status}')

    def on_order_stock_async_response(self, response):
        logger.debug(f'异步下单回报: order_id={response.order_id}')
