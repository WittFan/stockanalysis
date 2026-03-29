"""
测试公共 fixtures
全程使用真实 duck.db，通过限定 symbol + 日期范围控制查询量
"""
import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from engine.proj_config import ProjConfig
from engine.algos import SelectAll, WeightEqually, Rebalance, RunMonthly


# ---- 公共测试常量 ----

# 使用少量 ETF 标的 + 1 年数据，控制查询量
TEST_SYMBOLS = ['510300.SH', '159915.SZ', '511220.SH']
TEST_START = '20210101'
TEST_END = '20211231'
TEST_BENCHMARK = '000300.SH'


@pytest.fixture(scope='session')
def simple_config():
    """
    最小化 ProjConfig，用于简单策略回测测试。
    SelectAll + WeightEqually + Rebalance + RunMonthly（月度调仓）
    """
    config = ProjConfig(
        name='test_simple',
        symbols=TEST_SYMBOLS,
        start_date=TEST_START,
        end_date=TEST_END,
        initial_capital=1_000_000.0,
        commission=0.0001,
        slippage=0.0001,
        benchmark=TEST_BENCHMARK,
        data_folder='etfs',
    )
    config.algos = [
        RunMonthly(),
        SelectAll(),
        WeightEqually(),
        Rebalance(),
    ]
    return config
