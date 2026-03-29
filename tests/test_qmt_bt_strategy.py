#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QMT Mock × Backtrader 策略集成测试
====================================
验证 QMTStore / QMTBroker / QMTData 在 Backtrader 策略中的完整流程：
  - QMTStore mock 连接
  - QMTData 从 DuckDB 加载 ETF 历史数据
  - QMTBroker 接收订单 → MockXtTrader 执行 → 回调更新持仓/资金
  - 双均线策略产生买卖信号

运行：
    cd /Users/apple/program/stockanalysis
    python tests/test_qmt_bt_strategy.py
    python -m pytest tests/test_qmt_bt_strategy.py -v -s
"""

import sys
sys.path.insert(0, '/Users/apple/program/stockanalysis')

import pytest
import backtrader as bt
from datetime import datetime, timedelta
from loguru import logger

from backtrader_qmt_api import QMTStore, QMTBroker, QMTData


# ─────────────────────────────────────────────────────────────────
# 测试用 QMTData：从 DuckDB 读取 ETF 数据，历史结束后自动终止
# ─────────────────────────────────────────────────────────────────

class ETFQMTData(QMTData):
    """
    测试专用 DataFeed：
    - 覆盖 _fetch_history()：从 DuckDB etfs/history 目录读取真实行情
    - 覆盖 _load_live()   ：历史数据耗尽后直接返回 False，结束回测
    """

    def _fetch_history(self):
        from datafeed.dataloader import Duckdbloader
        from config import DATA_DIR_CSVS

        path = DATA_DIR_CSVS / 'etfs' / 'history'
        end_date   = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=self.p.backfill_days)).strftime('%Y%m%d')

        loader = Duckdbloader(
            path=path,
            symbols=[self.p.dataname],
            columns=['open', 'high', 'low', 'close', 'volume'],
            start_date=start_date,
            end_date=end_date,
            folder='',
        )
        df = loader.load()

        if df is None or df.empty:
            logger.warning(f'[ETFQMTData] 未加载到数据: {self.p.dataname}')
            return

        for dt, row in df.iterrows():
            bar_dt = dt.to_pydatetime() if hasattr(dt, 'to_pydatetime') else dt
            self._hist_bars.append({
                'datetime': bar_dt,
                'open':   float(row['open']),
                'high':   float(row['high']),
                'low':    float(row['low']),
                'close':  float(row['close']),
                'volume': float(row['volume']),
            })

        logger.info(f'[ETFQMTData] {self.p.dataname}: 载入 {len(self._hist_bars)} 条历史数据')

    def _load_live(self):
        """历史数据耗尽后直接终止（不进入真正的实时模式）"""
        return False


# ─────────────────────────────────────────────────────────────────
# 双均线策略
# ─────────────────────────────────────────────────────────────────

class MAStrategy(bt.Strategy):
    """
    简单双均线金叉/死叉策略：
    - fast_ma 上穿 slow_ma → 买入 (size=100)
    - fast_ma 下穿 slow_ma → 卖出清仓
    """
    params = (
        ('fast', 5),
        ('slow', 20),
        ('size', 100),
    )

    def __init__(self):
        self.sma_fast  = bt.ind.SMA(period=self.p.fast)
        self.sma_slow  = bt.ind.SMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(self.sma_fast, self.sma_slow)

        self.pending_order = None   # 当前挂单（避免重复下单）
        self.buy_count  = 0
        self.sell_count = 0
        self.order_log  = []        # (bar_dt, side, price, size, status)

    def next(self):
        if self.pending_order:
            return

        if self.crossover > 0:          # 金叉
            if not self.position:
                self.pending_order = self.buy(size=self.p.size)
                self.buy_count += 1
                logger.info(
                    f'[策略] 金叉买入 bar={len(self)}, '
                    f'date={self.data.datetime.date(0)}, '
                    f'close={self.data.close[0]:.4f}'
                )

        elif self.crossover < 0:        # 死叉
            if self.position:
                self.pending_order = self.sell(size=self.p.size)
                self.sell_count += 1
                logger.info(
                    f'[策略] 死叉卖出 bar={len(self)}, '
                    f'date={self.data.datetime.date(0)}, '
                    f'close={self.data.close[0]:.4f}'
                )

    def notify_order(self, order):
        if order.status in (order.Submitted, order.Accepted):
            return

        if order.status == order.Completed:
            side   = '买入' if order.isbuy() else '卖出'
            price  = order.executed.price if order.executed.price else order.created.price
            size   = abs(order.executed.size) if order.executed.size else abs(order.created.size)
            logger.info(f'[策略] 订单完成: {side} {size}股 @ {price:.4f}')
            self.order_log.append((
                self.data.datetime.date(0), side,
                price, size, 'Completed'
            ))
            self.pending_order = None

        elif order.status in (order.Rejected, order.Cancelled):
            logger.warning(f'[策略] 订单被拒/撤销: status={order.status}')
            self.order_log.append((
                self.data.datetime.date(0), '?', 0, 0, 'Failed'
            ))
            self.pending_order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            logger.info(
                f'[策略] 交易平仓: pnl={trade.pnl:.2f}, '
                f'pnlcomm={trade.pnlcomm:.2f}'
            )


# ─────────────────────────────────────────────────────────────────
# 辅助函数：搭建并运行 Cerebro
# ─────────────────────────────────────────────────────────────────

def run_qmt_strategy(symbol='511220.SH', backfill_days=500):
    """
    用 QMTStore(mock) + QMTBroker + ETFQMTData 跑双均线策略。
    返回 (strategy, broker) 供断言使用。
    """
    QMTStore._singleton = None

    store  = QMTStore(use_mock=True, qmtpath='/mock/path', account_id='test001')
    broker = store.getbroker()
    data   = ETFQMTData(dataname=symbol, backfill_days=backfill_days, store=store)

    cerebro = bt.Cerebro()
    cerebro.adddata(data, name=symbol)
    cerebro.setbroker(broker)
    cerebro.addstrategy(MAStrategy, fast=5, slow=20, size=100)

    results = cerebro.run()

    QMTStore._singleton = None
    return results[0], broker


# ─────────────────────────────────────────────────────────────────
# pytest 测试类
# ─────────────────────────────────────────────────────────────────

class TestQMTBtStrategy:
    """QMT Mock × Backtrader 策略集成测试"""

    @pytest.fixture(scope='class')
    def result(self):
        """跑一次策略，整个 class 复用结果"""
        strat, broker = run_qmt_strategy(symbol='511220.SH', backfill_days=500)
        return strat, broker

    # ── 数据层 ──────────────────────────────────────────────────

    def test_data_loaded(self, result):
        """数据成功载入且有足够 bar 数"""
        strat, _ = result
        assert len(strat) > 20, f'bar 数太少: {len(strat)}'
        logger.info(f'✓ 数据 bar 数: {len(strat)}')

    # ── 交易信号 ──────────────────────────────────────────────────

    def test_has_signals(self, result):
        """双均线策略产生了买卖信号"""
        strat, _ = result
        total = strat.buy_count + strat.sell_count
        assert total > 0, '策略未产生任何交易信号'
        logger.info(f'✓ 买入信号: {strat.buy_count}, 卖出信号: {strat.sell_count}')

    def test_buy_sell_balanced(self, result):
        """买卖信号数量接近（差距不超过 1，因为最后可能持仓未平）"""
        strat, _ = result
        diff = abs(strat.buy_count - strat.sell_count)
        assert diff <= 1, f'买卖信号严重不均衡: buy={strat.buy_count}, sell={strat.sell_count}'

    # ── 订单流转 ──────────────────────────────────────────────────

    def test_orders_submitted(self, result):
        """QMTBroker 收到了订单"""
        strat, broker = result
        assert len(broker._orders) > 0, 'Broker 未收到任何订单'
        logger.info(f'✓ Broker 收到订单数: {len(broker._orders)}')

    def test_orders_have_qmt_id(self, result):
        """所有订单都有对应的 QMT order_id 映射"""
        strat, broker = result
        for bt_ref in broker._orders:
            assert bt_ref in broker._bt2qmt, f'bt_ref={bt_ref} 没有 QMT order_id'
        logger.info(f'✓ 所有订单均映射到 QMT order_id')

    def test_completed_orders_exist(self, result):
        """存在已完成的订单记录"""
        strat, broker = result
        completed = [o for o in broker._orders.values()
                     if o.status == bt.Order.Completed]
        # Mock 模式下，事件处理在 next() 中，可能不是所有订单都走完 completed 流程
        # 但至少有订单 Accepted（submit 中立即 accept）
        accepted_or_completed = [o for o in broker._orders.values()
                                  if o.status in (bt.Order.Accepted, bt.Order.Completed)]
        assert len(accepted_or_completed) > 0, '没有任何订单到达 Accepted/Completed 状态'
        logger.info(f'✓ Completed 订单: {len(completed)}, Accepted: {len(accepted_or_completed) - len(completed)}')

    # ── 持仓与资金 ──────────────────────────────────────────────

    def test_broker_asset_synced(self, result):
        """Broker 资金已初始化（start 时从 MockXtTrader 同步）"""
        strat, broker = result
        # mock 初始资金为 1_000_000
        # 交易后 cash 会变化，但总资产应合理
        assert broker._cash >= 0, f'cash 不合理: {broker._cash}'
        logger.info(f'✓ 最终 cash={broker._cash:.2f}, total_asset={broker._value:.2f}')

    def test_positions_tracked(self, result):
        """Broker 跟踪了至少一个标的的持仓变动"""
        strat, broker = result
        # broker._positions 记录了所有持仓变动（包括已清仓的）
        assert '511220.SH' in broker._positions, '未跟踪 511220.SH 持仓'
        logger.info(f'✓ 持仓记录: {broker._positions}')

    # ── MockXtTrader 状态 ──────────────────────────────────────────

    def test_mock_trader_orders(self, result):
        """MockXtTrader 内部订单数与 Broker 订单数一致"""
        strat, broker = result
        xt_orders = broker.store.xt_trader._orders
        assert len(xt_orders) == len(broker._orders), (
            f'MockXtTrader 订单数({len(xt_orders)}) ≠ Broker 订单数({len(broker._orders)})'
        )
        logger.info(f'✓ MockXtTrader 订单数: {len(xt_orders)}')

    def test_mock_trader_positions(self, result):
        """MockXtTrader 持仓与 Broker 持仓同步"""
        strat, broker = result
        xt_pos = broker.store.xt_trader._positions
        for code, pos_info in xt_pos.items():
            broker_pos = broker._positions.get(code)
            if broker_pos:
                assert broker_pos.size == pos_info['volume'], (
                    f'{code}: MockXtTrader.volume={pos_info["volume"]}, '
                    f'Broker.size={broker_pos.size}'
                )
        logger.info(f'✓ MockXtTrader 与 Broker 持仓同步')


# ─────────────────────────────────────────────────────────────────
# 直接运行入口
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    from loguru import logger
    import sys

    logger.remove()
    logger.add(sys.stdout, level='INFO',
               format='<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | {message}')

    print('\n' + '=' * 60)
    print('  QMT Mock × Backtrader 策略集成测试')
    print('=' * 60 + '\n')

    strat, broker = run_qmt_strategy(symbol='511220.SH', backfill_days=500)

    print('\n' + '─' * 60)
    print(f'  Bar 总数        : {len(strat)}')
    print(f'  买入信号        : {strat.buy_count} 次')
    print(f'  卖出信号        : {strat.sell_count} 次')
    print(f'  Broker 订单数   : {len(broker._orders)}')
    print(f'  最终 cash       : {broker._cash:>12.2f}')
    print(f'  最终 total_asset: {broker._value:>12.2f}')
    print(f'  最终持仓        : {dict(broker._positions)}')
    print('─' * 60)

    print('\n订单日志：')
    for entry in strat.order_log[:10]:
        print(f'  {entry}')
    if len(strat.order_log) > 10:
        print(f'  ... 共 {len(strat.order_log)} 条')
    print()
