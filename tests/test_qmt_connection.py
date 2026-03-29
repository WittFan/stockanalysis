#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
backtrader_qmt_api Windows 实机连接测试
=========================================
用途：
1. 在 Windows 环境下测试与 MiniQMT 客户端的真实连接
2. 验证 xtdata 和 xttrader 各项功能
3. 测试行情订阅和订单流转

运行前提：
- Windows 操作系统
- MiniQMT 客户端已启动
- 已配置正确的 userdata_mini 路径和资金账号

运行方式：
    cd /Users/apple/program/stockanalysis
    python tests/test_qmt_connection.py

配置方式（选择其一）：
1. 修改 setting.py 中的 qmtpath 和 qmtaccount
2. 设置环境变量：QMT_PATH 和 QMT_ACCOUNT
"""

import os
import sys
import time
import traceback
from datetime import datetime, timedelta

# 确保能导入项目模块
sys.path.insert(0, '/Users/apple/program/stockanalysis')

# 导入前先检查是否在 Windows 环境
IS_WINDOWS = sys.platform.startswith('win')


def check_prerequisites():
    """检查运行前提条件"""
    print("=" * 60)
    print("backtrader_qmt_api Windows 实机连接测试")
    print("=" * 60)
    
    if not IS_WINDOWS:
        print("\n⚠️ 警告：当前不是 Windows 环境")
        print("本测试需要在 Windows 上运行，且 MiniQMT 客户端已启动")
        print("在 Mac/Linux 上请使用: python tests/test_qmt_mock.py\n")
        return False
    
    print(f"\n✅ 操作系统: {sys.platform}")
    
    # 检查 xtquant 是否可导入
    try:
        from xtquant import xtdata, xttrader, xtconstant, xttype
        print("✅ xtquant 模块可导入")
    except ImportError as e:
        print(f"❌ xtquant 模块导入失败: {e}")
        print("请确保 xtquant 已正确安装")
        return False
    
    return True


def get_config():
    """获取配置，优先级：环境变量 > setting.py > 默认"""
    config = {
        'qmtpath': r'D:\迅投极速交易终端\userdata_mini',
        'account_id': '1000000365',
        'session_id': 123456,
        'test_stock': '000001.SZ',  # 平安银行，用于测试
    }
    
    # 尝试从环境变量读取
    if os.environ.get('QMT_PATH'):
        config['qmtpath'] = os.environ.get('QMT_PATH')
    if os.environ.get('QMT_ACCOUNT'):
        config['account_id'] = os.environ.get('QMT_ACCOUNT')
    if os.environ.get('QMT_SESSION'):
        config['session_id'] = int(os.environ.get('QMT_SESSION'))
    
    # 尝试从 setting.py 读取
    try:
        import setting
        if hasattr(setting, 'qmtpath'):
            config['qmtpath'] = setting.qmtpath
        if hasattr(setting, 'qmtaccount'):
            config['account_id'] = setting.qmtaccount
        if hasattr(setting, 'session_id'):
            config['session_id'] = setting.session_id
        print("✅ 已从 setting.py 加载配置")
    except ImportError:
        print("⚠️ setting.py 不存在，使用默认/环境变量配置")
    
    return config


def test_xtdata_basic(config):
    """测试 xtdata 基本功能"""
    print("\n" + "-" * 60)
    print("测试 1: xtdata 基本功能")
    print("-" * 60)
    
    try:
        from xtquant import xtdata
        
        # 1.1 获取合约信息
        print("\n1.1 获取合约信息...")
        stock_code = config['test_stock']
        detail = xtdata.get_instrument_detail(stock_code)
        if detail:
            print(f"   ✅ 合约信息: {stock_code}")
            print(f"      - 名称: {detail.get('InstrumentName', 'N/A')}")
            print(f"      - 交易所: {detail.get('ExchangeID', 'N/A')}")
            print(f"      - 涨停价: {detail.get('UpStopPrice', 'N/A')}")
            print(f"      - 跌停价: {detail.get('DownStopPrice', 'N/A')}")
        else:
            print(f"   ⚠️ 无法获取合约信息: {stock_code}")
        
        # 1.2 获取历史数据
        print("\n1.2 获取历史 K 线数据...")
        end_time = datetime.now().strftime('%Y%m%d')
        start_time = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
        
        data = xtdata.get_market_data(
            field_list=['open', 'high', 'low', 'close', 'volume'],
            stock_list=[stock_code],
            period='1d',
            start_time=start_time,
            end_time=end_time,
            dividend_type='none',
            fill_data=True
        )
        
        if data and 'close' in data:
            df = data['close']
            print(f"   ✅ 获取到历史数据")
            print(f"      - 数据条数: {len(df.columns)}")
            print(f"      - 时间范围: {df.columns[0]} ~ {df.columns[-1]}")
            print(f"      - 最新收盘价: {df.loc[stock_code, df.columns[-1]]}")
        else:
            print(f"   ❌ 未获取到历史数据")
            return False
        
        # 1.3 获取全推行情
        print("\n1.3 获取全推行情...")
        tick_data = xtdata.get_full_tick([stock_code])
        if tick_data and stock_code in tick_data:
            tick = tick_data[stock_code]
            print(f"   ✅ 获取到全推行情")
            print(f"      - 最新价: {tick.get('lastPrice', 'N/A')}")
            print(f"      - 开盘价: {tick.get('open', 'N/A')}")
            print(f"      - 成交量: {tick.get('volume', 'N/A')}")
        else:
            print(f"   ⚠️ 无法获取全推行情")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        traceback.print_exc()
        return False


def test_xtdata_subscription(config):
    """测试 xtdata 实时订阅"""
    print("\n" + "-" * 60)
    print("测试 2: xtdata 实时行情订阅")
    print("-" * 60)
    
    try:
        from xtquant import xtdata
        import threading
        
        received_data = []
        
        def on_quote(datas):
            """行情回调"""
            received_data.append(datas)
            stock_code = config['test_stock']
            if stock_code in datas:
                data = datas[stock_code]
                print(f"   📊 收到行情推送: {stock_code}, close={data.get('close', 'N/A')}")
        
        # 2.1 订阅单股行情
        print("\n2.1 订阅单股行情...")
        stock_code = config['test_stock']
        seq = xtdata.subscribe_quote(
            stock_code,
            period='1d',
            callback=on_quote
        )
        
        if seq > 0:
            print(f"   ✅ 订阅成功，订阅号: {seq}")
        else:
            print(f"   ❌ 订阅失败")
            return False
        
        # 2.2 等待回调
        print("\n2.2 等待行情回调（最多 5 秒）...")
        
        # 在单独线程中运行 xtdata.run()
        def run_xtdata():
            try:
                xtdata.run()
            except:
                pass
        
        # 由于 run() 会阻塞，我们在非 Windows 环境直接跳过
        # 在 Windows 环境可以尝试启动线程
        if IS_WINDOWS:
            run_thread = threading.Thread(target=run_xtdata, daemon=True)
            run_thread.start()
            
            # 等待接收数据
            for i in range(5):
                if received_data:
                    break
                time.sleep(1)
                print(f"   等待中... {i+1}s")
            
            # 取消订阅
            xtdata.unsubscribe_quote(seq)
            
            if received_data:
                print(f"   ✅ 收到 {len(received_data)} 次行情推送")
            else:
                print(f"   ⚠️ 未收到实时推送（可能是非交易时间）")
        else:
            print("   ⏭️ 跳过实时订阅测试（非 Windows 环境）")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        traceback.print_exc()
        return False


def test_xttrader_connection(config):
    """测试 xttrader 连接"""
    print("\n" + "-" * 60)
    print("测试 3: xttrader 连接和基本功能")
    print("-" * 60)
    
    try:
        from xtquant import xttrader, xttype
        
        # 3.1 创建 XtQuantTrader 实例
        print("\n3.1 创建 XtQuantTrader 实例...")
        path = config['qmtpath']
        session_id = config['session_id']
        
        if not os.path.exists(path):
            print(f"   ❌ MiniQMT 路径不存在: {path}")
            print(f"   请确认 MiniQMT 已安装，并修改 setting.py 或环境变量 QMT_PATH")
            return False
        
        xt_trader = xttrader.XtQuantTrader(path, session_id)
        print(f"   ✅ 实例创建成功")
        
        # 3.2 注册回调
        print("\n3.2 注册回调...")
        
        class TestCallback(xttrader.XtQuantTraderCallback):
            def on_disconnected(self):
                print("   ⚠️ 连接断开回调")
            
            def on_stock_order(self, order):
                print(f"   📋 委托回调: {order.stock_code}, status={order.order_status}")
            
            def on_stock_trade(self, trade):
                print(f"   💰 成交回调: {trade.stock_code}, vol={trade.traded_volume}")
        
        callback = TestCallback()
        xt_trader.register_callback(callback)
        print("   ✅ 回调注册成功")
        
        # 3.3 启动和连接
        print("\n3.3 启动和连接...")
        xt_trader.start()
        result = xt_trader.connect()
        
        if result == 0:
            print("   ✅ 连接成功")
        else:
            print(f"   ❌ 连接失败，返回码: {result}")
            print("   请确认 MiniQMT 客户端已启动")
            return False
        
        # 3.4 创建账号并订阅
        print("\n3.4 订阅账号...")
        account = xttype.StockAccount(config['account_id'])
        sub_result = xt_trader.subscribe(account)
        
        if sub_result == 0:
            print(f"   ✅ 账号订阅成功: {config['account_id']}")
        else:
            print(f"   ❌ 账号订阅失败，返回码: {sub_result}")
            return False
        
        # 3.5 查询资产
        print("\n3.5 查询资金资产...")
        asset = xt_trader.query_stock_asset(account)
        if asset:
            print(f"   ✅ 资金查询成功")
            print(f"      - 可用资金: {asset.cash:,.2f}")
            print(f"      - 冻结资金: {asset.frozen_cash:,.2f}")
            print(f"      - 持仓市值: {asset.market_value:,.2f}")
            print(f"      - 总资产: {asset.total_asset:,.2f}")
        else:
            print(f"   ⚠️ 无法查询资金（可能是未登录或账号错误）")
        
        # 3.6 查询持仓
        print("\n3.6 查询持仓...")
        positions = xt_trader.query_stock_positions(account)
        if positions:
            print(f"   ✅ 持仓查询成功，共 {len(positions)} 只标的")
            for pos in positions[:3]:  # 只显示前3只
                print(f"      - {pos.stock_code}: {pos.volume}股, 成本{pos.avg_price:.2f}")
        else:
            print(f"   ℹ️ 当前无持仓")
        
        # 3.7 查询当日委托
        print("\n3.7 查询当日委托...")
        orders = xt_trader.query_stock_orders(account)
        if orders:
            print(f"   ✅ 委托查询成功，共 {len(orders)} 条委托")
        else:
            print(f"   ℹ️ 当日无委托")
        
        # 3.8 停止
        print("\n3.8 停止连接...")
        xt_trader.stop()
        print("   ✅ 已停止")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        traceback.print_exc()
        return False


def test_backtrader_qmt_integration(config):
    """测试 backtrader_qmt_api 集成"""
    print("\n" + "-" * 60)
    print("测试 4: backtrader_qmt_api 集成测试")
    print("-" * 60)
    
    try:
        from backtrader_qmt_api import QMTStore, QMTBroker, QMTData
        
        # 4.1 创建 Store
        print("\n4.1 创建 QMTStore...")
        
        # 先重置单例
        QMTStore._singleton = None
        
        store = QMTStore(
            qmtpath=config['qmtpath'],
            account_id=config['account_id'],
            session_id=config['session_id']
        )
        print("   ✅ QMTStore 创建成功")
        
        # 4.2 连接
        print("\n4.2 连接 MiniQMT...")
        if not os.path.exists(config['qmtpath']):
            print("   ⏭️ 跳过（MiniQMT 路径不存在）")
            return True
        
        result = store.connect()
        if result:
            print("   ✅ 连接成功")
        else:
            print("   ❌ 连接失败")
            return False
        
        # 4.3 获取 Broker
        print("\n4.3 获取 QMTBroker...")
        broker = store.getbroker()
        broker.start()
        print("   ✅ Broker 启动成功")
        
        # 4.4 验证资金查询
        print("\n4.4 验证资金查询...")
        cash = broker.getcash()
        value = broker.getvalue()
        print(f"   ✅ 可用资金: {cash:,.2f}, 总资产: {value:,.2f}")
        
        # 4.5 获取 Data
        print("\n4.5 获取 QMTData...")
        data = store.getdata(
            dataname=config['test_stock'],
            backfill_days=5
        )
        data.start()
        print(f"   ✅ Data 启动成功: {config['test_stock']}")
        
        # 4.6 尝试获取历史数据
        print("\n4.6 尝试获取历史数据...")
        # 触发 _load_start 加载历史数据
        # 注意：这里只是启动，实际数据在 Backtrader run 时才会加载
        print("   ℹ️ 历史数据将在 Backtrader Cerebro.run() 时加载")
        
        # 4.7 清理
        print("\n4.7 清理资源...")
        data.stop()
        broker.stop()
        store.stop()
        QMTStore._singleton = None
        print("   ✅ 资源已清理")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 检查前提条件
    if not check_prerequisites():
        if not IS_WINDOWS:
            print("提示: 在 Mac/Linux 上可以使用 Mock 模式进行开发测试")
            print("      运行: python tests/test_qmt_mock.py")
        return
    
    # 获取配置
    config = get_config()
    print(f"\n配置信息:")
    print(f"  - MiniQMT 路径: {config['qmtpath']}")
    print(f"  - 资金账号: {config['account_id']}")
    print(f"  - 会话ID: {config['session_id']}")
    print(f"  - 测试标的: {config['test_stock']}")
    
    # 运行测试
    results = []
    
    # 测试 1: xtdata 基本功能
    results.append(("xtdata 基本功能", test_xtdata_basic(config)))
    
    # 测试 2: xtdata 实时订阅
    results.append(("xtdata 实时订阅", test_xtdata_subscription(config)))
    
    # 测试 3: xttrader 连接
    results.append(("xttrader 连接", test_xttrader_connection(config)))
    
    # 测试 4: backtrader_qmt_api 集成
    results.append(("backtrader_qmt_api 集成", test_backtrader_qmt_integration(config)))
    
    # 测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"总计: {len(results)} 项, 通过: {passed}, 失败: {failed}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！backtrader_qmt_api 工作正常。")
    else:
        print(f"\n⚠️ 有 {failed} 项测试失败，请检查配置和 MiniQMT 状态。")


if __name__ == '__main__':
    main()
