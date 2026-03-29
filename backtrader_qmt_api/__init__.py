#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
backtrader_qmt_api — Backtrader × QMT (迅投MiniQMT) 桥接层

主要类：
- QMTStore   : 连接管理（MetaSingleton，XtQuantTraderCallback）
- QMTBroker  : 订单/持仓/资金管理（BrokerBase）
- QMTData    : 行情数据（DataBase，历史回填 + 实时订阅）
- MockXtTrader / MockXtData : 离线开发 Mock

用法::

    from backtrader_qmt_api import QMTStore

    store = QMTStore(qmtpath=r'D:\\...\\userdata_mini',
                     account_id='1000000365',
                     use_mock=True)      # 开发阶段使用 mock
    broker = store.getbroker()
    data   = store.getdata(dataname='511220.SH', backfill_days=30)
"""

from .qmtstore import QMTStore
from .qmtbroker import QMTBroker
from .qmtdata import QMTData
from .mock import MockXtTrader, MockXtData, MockStockAccount

__all__ = [
    'QMTStore',
    'QMTBroker',
    'QMTData',
    'MockXtTrader',
    'MockXtData',
    'MockStockAccount',
]
