#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
backtrader_qmt_api Mock 模式测试
================================
用途：
1. 在无 QMT 客户端环境下验证 backtrader_qmt_api 功能
2. 测试 QMTStore、QMTBroker、QMTData 的基本功能
3. 验证订单流转和持仓同步逻辑

运行方式：
    cd /Users/apple/program/stockanalysis
    python -m pytest tests/test_qmt_mock.py -v
    # 或单独运行
    python tests/test_qmt_mock.py
"""

import sys
import time
import pytest
from datetime import datetime, timedelta

# 确保能导入项目模块
sys.path.insert(0, '/Users/apple/program/stockanalysis')

from backtrader_qmt_api import QMTStore, QMTBroker, QMTData
from backtrader_qmt_api.mock import MockXtTrader, MockXtData, MockStockAccount


class TestQMTStoreMock:
    """QMTStore Mock 模式测试"""
    
    def test_store_singleton(self):
        """测试 Store 单例模式"""
        # 重置单例（通过私有属性）
        QMTStore._singleton = None
        
        store1 = QMTStore(use_mock=True, qmtpath='/mock/path', account_id='123456')
        store2 = QMTStore(use_mock=True, qmtpath='/mock/path', account_id='123456')
        
        # 验证是同一个实例
        assert store1 is store2
        
        # 清理
        QMTStore._singleton = None
    
    def test_store_init_params(self):
        """测试 Store 初始化参数"""
        QMTStore._singleton = None
        
        store = QMTStore(
            use_mock=True,
            qmtpath=r'D:\Test\userdata_mini',
            account_id='1000000365',
            session_id=123456
        )
        
        assert store.p.use_mock is True
        assert store.p.qmtpath == r'D:\Test\userdata_mini'
        assert store.p.account_id == '1000000365'
        assert store.p.session_id == 123456
        
        QMTStore._singleton = None
    
    def test_store_connect_mock(self):
        """测试 Mock 模式连接"""
        QMTStore._singleton = None
        
        store = QMTStore(use_mock=True)
        result = store.connect()
        
        assert result is True
        assert store.connected is True
        assert store.xt_trader is not None
        assert store.account is not None
        
        store.stop()
        QMTStore._singleton = None
    
    def test_store_factory_methods(self):
        """测试 Store 工厂方法 getbroker/getdata"""
        QMTStore._singleton = None
        
        store = QMTStore(use_mock=True)
        store.connect()
        
        # 测试 getbroker
        broker = store.getbroker()
        assert broker is not None
        assert isinstance(broker, QMTBroker)
        assert broker.store is store
        
        # 测试 getdata
        data = store.getdata(dataname='000001.SZ')
        assert data is not None
        assert isinstance(data, QMTData)
        assert data._store is store
        
        store.stop()
        QMTStore._singleton = None


class TestQMTBrokerMock:
    """QMTBroker Mock 模式测试"""
    
    @pytest.fixture
    def broker(self):
        """创建并初始化 Broker"""
        QMTStore._singleton = None
        store = QMTStore(use_mock=True)
        store.connect()
        broker = store.getbroker()
        broker.start()
        yield broker
        broker.stop()
        store.stop()
        QMTStore._singleton = None
    
    def test_broker_initial_sync(self, broker):
        """测试 Broker 初始同步（持仓和资金）"""
        # Mock 模式下初始资金应为 1_000_000
        assert broker.getcash() == 1_000_000.0
        assert broker.getvalue() == 1_000_000.0
        
        # Mock 模式下初始持仓为空
        positions = broker._positions
        assert len(positions) == 0
    
    def test_broker_getposition(self, broker):
        """测试获取持仓"""
        from backtrader import Position
        
        # 创建一个 mock data
        class MockData:
            class p:
                dataname = '000001.SZ'
        
        data = MockData()
        pos = broker.getposition(data)
        
        # 无持仓时返回空的 Position
        assert isinstance(pos, Position)
        assert pos.size == 0
    
    def test_broker_submit_order(self, broker):
        """测试提交订单"""
        from backtrader import Order
        
        # 创建 mock order（模拟 Backtrader Order 的关键方法）
        class MockData:
            class p:
                dataname = '000001.SZ'
        
        class MockOrder:
            _ref_counter = [0]  # 使用列表作为可变引用
            
            def __init__(self):
                MockOrder._ref_counter[0] += 1
                self.ref = MockOrder._ref_counter[0]
                self.data = MockData()
                self.created = type('obj', (object,), {
                    'size': 100,
                    'price': 10.0
                })()
                self.status = Order.Created
                self.exectype = Order.Limit  # 限价单
                
            def isbuy(self):
                return True
                
            def submit(self, broker):
                self.status = Order.Submitted
                
            def accept(self, broker):
                self.status = Order.Accepted

            def reject(self, broker):
                self.status = Order.Rejected

            def completed(self):
                self.status = Order.Completed

            def partial(self):
                self.status = Order.Partial

            def cancel(self):
                self.status = Order.Cancelled

            def execute(self, dt, size, price, closed, closedvalue, closedcomm,
                        opened, openedvalue, openedcomm, margin, pnl, psize, pprice):
                pass

            def clone(self):
                import copy
                return copy.copy(self)

        order = MockOrder()

        # 提交订单
        result = broker.submit(order)

        # 验证订单被接受
        assert result.ref == order.ref
        assert order.ref in broker._orders
        assert order.ref in broker._bt2qmt  # 有对应的 QMT order_id
    
    def test_broker_order_status_mapping(self, broker):
        """测试订单状态映射"""
        from backtrader import Order
        
        # 验证状态映射表完整
        assert broker._ORDER_STATUS_MAP[48] is None  # ORDER_UNREPORTED
        assert broker._ORDER_STATUS_MAP[49] is None  # ORDER_WAIT_REPORTING
        assert broker._ORDER_STATUS_MAP[50] == Order.Accepted  # 2
        assert broker._ORDER_STATUS_MAP[56] == Order.Completed  # 4
        assert broker._ORDER_STATUS_MAP[54] == Order.Cancelled  # 5
        assert broker._ORDER_STATUS_MAP[57] == Order.Rejected  # 8


class TestQMTDataMock:
    """QMTData Mock 模式测试"""
    
    @pytest.fixture
    def data(self):
        """创建 QMTData 实例"""
        QMTStore._singleton = None
        store = QMTStore(use_mock=True)
        store.connect()
        data = store.getdata(dataname='000001.SZ', backfill_days=5)
        yield data
        store.stop()
        QMTStore._singleton = None
    
    def test_data_init(self, data):
        """测试 Data 初始化"""
        assert data.p.dataname == '000001.SZ'
        assert data.p.backfill_days == 5
        assert data._state == data._ST_START
        assert data.islive() is True
    
    def test_data_state_machine(self, data):
        """测试 Data 状态机"""
        # 初始状态
        assert data._state == data._ST_START
        
        # 调用 start 方法（模拟 Backtrader 调用）
        data.start()
        
        # 由于 Mock 模式无法从 DuckDB 加载真实数据
        # 状态可能保持 START 或进入 LIVE（取决于是否有历史数据）
        assert data._state in [data._ST_START, data._ST_LIVE]
    
    def test_data_parse_quote(self, data):
        """测试行情数据解析"""
        # 测试正常行情数据
        quote_item = {
            'open': 10.0,
            'high': 10.5,
            'low': 9.8,
            'close': 10.2,
            'volume': 10000,
            'time': int(datetime.now().timestamp() * 1000)
        }
        
        bar = data._parse_quote_item(quote_item)
        
        assert bar is not None
        assert bar['open'] == 10.0
        assert bar['high'] == 10.5
        assert bar['low'] == 9.8
        assert bar['close'] == 10.2
        assert bar['volume'] == 10000
    
    def test_data_parse_invalid_quote(self, data):
        """测试无效行情数据解析"""
        # 测试收盘价为 0 的数据（应被过滤）
        quote_item = {
            'open': 0,
            'high': 0,
            'low': 0,
            'close': 0,
            'volume': 0
        }
        
        bar = data._parse_quote_item(quote_item)
        assert bar is None


class TestMockXtTrader:
    """MockXtTrader 功能测试"""
    
    def test_mock_trader_init(self):
        """测试 MockXtTrader 初始化"""
        trader = MockXtTrader('/mock/path', 123456)
        
        assert trader._path == '/mock/path'
        assert trader._session_id == 123456
        assert trader._cash == 1_000_000.0
        assert trader._total_asset == 1_000_000.0
    
    def test_mock_trader_connect(self):
        """测试 MockXtTrader 连接"""
        trader = MockXtTrader('/mock/path', 123456)
        
        result = trader.connect()
        assert result == 0
        assert trader._connected is True
    
    def test_mock_trader_order(self):
        """测试 MockXtTrader 下单"""
        trader = MockXtTrader('/mock/path', 123456)
        trader.connect()
        
        account = MockStockAccount('1000000365')
        
        # 模拟买入
        order_id = trader.order_stock(
            account,
            '000001.SZ',
            23,  # STOCK_BUY
            100,
            11,  # FIX_PRICE
            10.5,
            'test_strategy',
            'test_remark'
        )
        
        assert order_id > 0
        assert order_id in trader._orders
        assert trader._positions['000001.SZ']['volume'] == 100
        
        # 模拟卖出
        order_id2 = trader.order_stock(
            account,
            '000001.SZ',
            24,  # STOCK_SELL
            50,
            5,  # LATEST_PRICE
            0,
            'test_strategy',
            'test_remark'
        )
        
        assert order_id2 > order_id
        assert trader._positions['000001.SZ']['volume'] == 50
    
    def test_mock_trader_query(self):
        """测试 MockXtTrader 查询功能"""
        trader = MockXtTrader('/mock/path', 123456)
        trader.connect()
        account = MockStockAccount('1000000365')
        
        # 查询资产
        asset = trader.query_stock_asset(account)
        assert asset is not None
        assert asset.cash == 1_000_000.0
        assert asset.total_asset == 1_000_000.0
        
        # 查询持仓（初始为空）
        positions = trader.query_stock_positions(account)
        assert positions is not None
        assert len(positions) == 0
        
        # 下单后查询
        trader.order_stock(account, '000001.SZ', 23, 100, 11, 10.5, '', '')
        positions = trader.query_stock_positions(account)
        assert len(positions) == 1
        assert positions[0].stock_code == '000001.SZ'
        assert positions[0].volume == 100


class TestIntegrationMock:
    """集成测试 - Mock 模式完整流程"""
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        QMTStore._singleton = None
        
        # 1. 创建 Store 并连接
        store = QMTStore(use_mock=True)
        assert store.connect() is True
        
        # 2. 获取 Broker 并启动
        broker = store.getbroker()
        broker.start()
        
        # 3. 验证初始状态
        assert broker.getcash() == 1_000_000.0
        
        # 4. 获取 Data
        data = store.getdata(dataname='000001.SZ', backfill_days=5)
        data.start()
        
        # 5. 模拟下单（通过 Broker）
        from backtrader import Order
        
        class MockData:
            class p:
                dataname = '000001.SZ'
        
        class MockOrder:
            _ref_counter = [100]
            
            def __init__(self):
                MockOrder._ref_counter[0] += 1
                self.ref = MockOrder._ref_counter[0]
                self.data = MockData()
                self.created = type('obj', (object,), {
                    'size': 100,
                    'price': 10.0
                })()
                self.status = Order.Created
                self.exectype = Order.Limit
                
            def isbuy(self):
                return True
                
            def submit(self, broker):
                self.status = Order.Submitted
                
            def accept(self, broker):
                self.status = Order.Accepted

            def reject(self, broker):
                self.status = Order.Rejected

            def completed(self):
                self.status = Order.Completed

            def partial(self):
                self.status = Order.Partial

            def cancel(self):
                self.status = Order.Cancelled

            def execute(self, dt, size, price, closed, closedvalue, closedcomm,
                        opened, openedvalue, openedcomm, margin, pnl, psize, pprice):
                pass

            def clone(self):
                """克隆订单（简化实现）"""
                import copy
                return copy.copy(self)

        order = MockOrder()
        broker.submit(order)

        # 6. 验证订单状态
        assert order.ref in broker._orders

        # 7. 模拟 next() 调用处理事件（回调链修通后会处理 order/trade/position/asset 事件）
        broker.next()

        # 验证订单已完成（回调触发 order.completed()）
        assert order.status == Order.Completed

        # 8. 清理
        data.stop()
        broker.stop()
        store.stop()
        QMTStore._singleton = None


if __name__ == '__main__':
    # 直接运行测试
    pytest.main([__file__, '-v'])
