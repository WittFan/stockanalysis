"""
算子测试公共 fixtures
使用 MockTarget 替代真实 StrategyAlgo，隔离算子逻辑
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

from engine.algos import SelectAll, WeightEqually, Rebalance, RunMonthly


SYMBOLS = ['510300.SH', '159915.SZ', '511220.SH']


def make_price_series(n=60, base=100.0, seed=42):
    """生成随机收盘价序列"""
    np.random.seed(seed)
    returns = np.random.randn(n) * 0.01
    prices = base * np.cumprod(1 + returns)
    return prices


@pytest.fixture
def mock_target():
    """
    最小化 MockTarget，模拟 StrategyAlgo 的对外接口。
    算子只依赖 target.temp、target.symbols、target.df_bar、target.df_close。
    """
    target = MagicMock()
    target.symbols = SYMBOLS
    target.now = pd.Timestamp('2021-03-01')
    target.index = 20
    target.temp = {}
    target.perm = {}

    # 构造 df_bar（当日行情，symbol 为 index）
    target.df_bar = pd.DataFrame({
        'open':   [100.1, 50.2, 110.3],
        'high':   [102.0, 52.0, 112.0],
        'low':    [99.0,  49.0, 109.0],
        'close':  [101.5, 51.0, 111.0],
        'volume': [1e6, 5e5, 2e6],
    }, index=SYMBOLS)

    # 构造 df_close（历史收盘价透视表，index=Timestamp, columns=symbol）
    dates = pd.date_range('2021-01-04', periods=60, freq='B')
    df_close = pd.DataFrame(
        {sym: make_price_series(60, 100 + i * 10) for i, sym in enumerate(SYMBOLS)},
        index=dates
    )
    target.df_close = df_close

    # 构造 ctxs（用 MagicMock 占位）
    target.ctxs = {sym: MagicMock() for sym in SYMBOLS}
    for sym, ctx in target.ctxs.items():
        ctx.long_pos.return_value = None  # 默认无持仓

    return target
