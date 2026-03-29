#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QMT 连接封装
============
直接封装 xtquant.XtQuantTrader + StockAccount，
不依赖 Backtrader 适配层（backtrader_qmt_api）。

仅供 windows_service 内部使用。
"""

from loguru import logger
from xtquant.xttrader import XtQuantTraderCallback


class QMTTraderCallback(XtQuantTraderCallback):
    """
    异步交易事件回调处理器
    """
    
    def on_order_stock_async_response(self, response):
        """
        异步下单响应回调
        :param response: XtOrderResponse 对象，包含 order_id 等信息
        """
        try:
            logger.info(f'异步下单响应: order_id={response.order_id}, '
                       f'stock_code={response.stock_code}, '
                       f'error_msg={response.error_msg}')
        except Exception as e:
            logger.error(f'on_order_stock_async_response 处理异常: {e}')
    
    def on_cancel_order_stock_async_response(self, response):
        """
        异步撤单响应回调
        :param response: XtCancelOrderResponse 对象
        """
        try:
            logger.info(f'异步撤单响应: order_id={response.order_id}, '
                       f'error_msg={response.error_msg}')
        except Exception as e:
            logger.error(f'on_cancel_order_stock_async_response 处理异常: {e}')
    
    def on_connected(self):
        """连接成功推送"""
        logger.info('QMT 连接成功')
    
    def on_disconnected(self):
        """连接断开推送"""
        logger.warning('QMT 连接已断开')
    
    def on_account_status(self, status):
        """账户状态推送"""
        try:
            logger.debug(f'账户状态: {status.account_id}, 状态={status.account_status}')
        except Exception:
            pass
    
    def on_stock_asset(self, asset):
        """资产推送"""
        try:
            logger.debug(f'账户资产推送: cash={asset.cash}, asset_balance={asset.asset_balance}')
        except Exception:
            pass


class QMTConnection:
    """
    持有 XtQuantTrader 和 StockAccount 的最小连接对象。

    Attributes:
        xt_trader:  XtQuantTrader 实例（连接成功后可用）
        account:    StockAccount 实例
        connected:  是否已成功连接
    """

    def __init__(self, qmtpath: str, account_id: str, session_id: int):
        self.qmtpath    = qmtpath
        self.account_id = account_id
        self.session_id = session_id
        self.xt_trader  = None
        self.account    = None
        self.connected  = False

    def connect(self) -> bool:
        """连接 MiniQMT，成功返回 True"""
        try:
            from xtquant.xttrader import XtQuantTrader
            from xtquant.xttype import StockAccount
            
            # 创建回调处理器并传入 XtQuantTrader
            callback = QMTTraderCallback()
            self.xt_trader = XtQuantTrader(self.qmtpath, self.session_id, callback)
            self.account   = StockAccount(self.account_id)
            
            # 启动交易线程（必须在 connect 前调用）
            self.xt_trader.start()
            result = self.xt_trader.connect()
            if result == 0:
                self.xt_trader.subscribe(self.account)
                self.connected = True
                logger.info(f'MiniQMT 连接成功，账号: {self.account_id}')
                return True
            logger.error(f'MiniQMT 连接失败，返回码: {result}')
            return False
        except Exception as e:
            logger.exception(f'QMTConnection.connect 异常: {e}')
            return False

    def stop(self):
        """断开连接"""
        if self.xt_trader:
            try:
                self.xt_trader.stop()
            except Exception:
                pass
        self.connected = False
        logger.info('QMT 连接已断开')
