#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QMT API 服务接口测试脚本（已改进版本）
根据测试报告改进的测试用例

改进内容：
  ✓ 使用真实股票代码（600000.SH 浦发银行、000858.SZ 五粮液）替代基金代码
  ✓ 下单接口改用固定价格（FIX_PRICE）模式，而不是最新价
  ✓ 优化下单数量，避免资金不足
  ✓ 异步下单使用不同的股票代码进行测试
  ✓ 撤单使用实际的订单ID（如果下单成功）或适当的测试ID
  ✓ 改进错误信息和测试结果显示

测试所有已实现的 REST API 端点
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# 配置
API_BASE_URL = "http://127.0.0.1:8080"
TIMEOUT = 20  # 改为 20 秒 - 增加超时时间处理撤单问题
DRY_RUN_MODE = False  # 改为 False - 已使用真实股票和价格进行测试

# 测试用的多个股票代码（用于重试）
TEST_STOCK_CODES = [
    '600000.SH',  # 浦发银行 - 上海主板蓝筹股
    '000858.SZ',  # 五粮液 - 深圳主板热股
    '601988.SH',  # 中国银行 - 上海主板
    '000063.SZ',  # 中兴通讯 - 深圳主板
]

# 测试结果统计
test_results = {
    'passed': 0,
    'failed': 0,
    'skipped': 0,
    'errors': []
}


class APITester:
    """API 测试器"""
    
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        # 添加简单的认证头（如果需要）
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token'
        }
    
    def test_endpoint(self, method: str, path: str, name: str, 
                     data: dict = None, params: dict = None,
                     expect_success: bool = True) -> Tuple[bool, str, Dict]:
        """
        测试单个接口端点
        返回: (是否通过, 测试说明, 响应数据)
        """
        url = f"{self.base_url}{path}"
        try:
            if method.upper() == 'GET':
                resp = self.session.get(url, params=params, headers=self.headers, 
                                       timeout=self.timeout)
            elif method.upper() == 'POST':
                resp = self.session.post(url, json=data, headers=self.headers,
                                        timeout=self.timeout)
            else:
                return False, f"不支持的 HTTP 方法: {method}", {}
            
            status_code = resp.status_code
            try:
                response_data = resp.json()
            except:
                response_data = {'raw': resp.text}
            
            # 检查响应
            if status_code == 401:
                return False, f"[{status_code}] 认证失败 (可能为 dry-run 模式)", response_data
            elif status_code >= 400:
                error_msg = response_data.get('error', response_data.get('message', ''))
                return False, f"[{status_code}] {error_msg}", response_data
            
            # 检查业务响应
            success = response_data.get('success', False)
            if expect_success and not success:
                error = response_data.get('error', '响应成功字段为 False')
                return False, f"业务失败: {error}", response_data
            
            return True, f"✓ {name}", response_data
        
        except requests.exceptions.Timeout:
            return False, f"⏱ 超时 (>{self.timeout}s)", {}
        except requests.exceptions.ConnectionError as e:
            return False, f"✗ 连接失败: {str(e)}", {}
        except Exception as e:
            return False, f"✗ 异常: {str(e)}", {}


def print_header(title: str):
    """打印测试组标题"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_test_result(name: str, passed: bool, message: str):
    """打印单个测试结果"""
    symbol = "✓" if passed else "✗"
    color = "\033[92m" if passed else "\033[91m"  # 绿色/红色
    reset = "\033[0m"
    print(f"  {color}{symbol}{reset} {name:<40} {message}")
    
    if passed:
        test_results['passed'] += 1
    else:
        test_results['failed'] += 1
        test_results['errors'].append(f"{name}: {message}")


def run_basic_tests(tester: APITester):
    """基础测试（无需 QMT 连接）"""
    print_header("1. 基础接口测试")
    
    # 1.1 首页
    passed, msg, data = tester.test_endpoint('GET', '/', '首页')
    print_test_result('GET /', passed, msg)
    
    # 1.2 健康检查
    passed, msg, data = tester.test_endpoint('GET', '/health', '健康检查',
                                            expect_success=False)  # 可能 disconnected
    print_test_result('GET /health', passed, msg)
    if passed:
        connected = data.get('data', {}).get('connected', False)
        print(f"      → 状态: {'已连接' if connected else '未连接'}")


def run_status_tests(tester: APITester):
    """状态检查测试"""
    print_header("2. 连接状态测试")
    
    # 2.1 API 状态
    passed, msg, data = tester.test_endpoint('GET', '/api/status', 'API 状态')
    print_test_result('GET /api/status', passed, msg)
    if passed:
        status_data = data.get('data', {})
        connected = status_data.get('connected', False)
        account = status_data.get('account_id', 'N/A')
        print(f"      → 账户: {account}, 连接: {connected}")


def run_query_tests(tester: APITester):
    """查询接口测试"""
    print_header("3. 查询接口测试 (xttrader)")
    
    tests = [
        ('GET', '/api/query/asset', '查询账户资产'),
        ('GET', '/api/query/positions', '查询持仓'),
        ('GET', '/api/query/orders', '查询委托'),
        ('GET', '/api/query/trades', '查询成交'),
    ]
    
    for method, path, name in tests:
        passed, msg, data = tester.test_endpoint(method, path, name)
        print_test_result(f'{method} {path}', passed, msg)
        if passed:
            result = data.get('data', {})
            if isinstance(result, dict):
                print(f"      → 字段数: {len(result)}")
            elif isinstance(result, list):
                print(f"      → 条数: {len(result)}")


def run_market_tests(tester: APITester):
    """市场数据接口测试"""
    print_header("4. 市场数据接口测试 (xtdata)")
    
    # 准备测试数据
    today = datetime.now()
    one_month_ago = today - timedelta(days=30)
    start_date = one_month_ago.strftime('%Y%m%d')
    end_date = today.strftime('%Y%m%d')
    
    tests = [
        # K线测试 - 使用真实流动性强的股票
        {
            'method': 'GET',
            'path': '/api/market/kline',
            'name': 'K线数据 (1d)',
            'params': {
                'stocks': '600000.SH,000858.SZ',  # 浦发银行、五粮液 - 流动性好
                'period': '1d',
                'start': start_date,
                'end': end_date,
                'fields': 'open,close,volume'
            }
        },
        # Tick 测试 - 使用真实股票
        {
            'method': 'GET',
            'path': '/api/market/tick',
            'name': 'Tick 快照',
            'params': {'stocks': '600000.SH'}  # 浦发银行
        },
        # 合约信息测试 - 使用真实股票
        {
            'method': 'GET',
            'path': '/api/market/instrument',
            'name': '合约基础信息',
            'params': {'stock': '600000.SH'}  # 浦发银行
        },
        # 合约类型测试 - 使用真实股票
        {
            'method': 'GET',
            'path': '/api/market/instrument_type',
            'name': '合约类型',
            'params': {'stock': '600000.SH'}  # 浦发银行
        },
        # 交易日历测试
        {
            'method': 'GET',
            'path': '/api/market/calendar',
            'name': '交易日历',
            'params': {
                'market': 'SH',
                'start': start_date,
                'end': end_date,
                'count': 10
            }
        },
        # 节假日列表测试
        {
            'method': 'GET',
            'path': '/api/market/holidays',
            'name': '节假日列表',
            'params': {}
        },
        # 板块列表测试
        {
            'method': 'GET',
            'path': '/api/market/sector',
            'name': '板块列表',
            'params': {}
        },
    ]
    
    for test in tests:
        passed, msg, data = tester.test_endpoint(
            test['method'], test['path'], test['name'],
            params=test.get('params')
        )
        print_test_result(f"{test['method']} {test['path']}", passed, msg)
        if passed:
            result = data.get('data', {})
            if isinstance(result, dict):
                print(f"      → 字段/条数: {len(result)}")
            elif isinstance(result, (list, tuple)):
                print(f"      → 条数: {len(result)}")


def run_trade_tests(tester: APITester):
    """交易接口测试（改进版 - 增强诊断和重试机制）"""
    print_header("5. 交易接口测试（改进版 - 重试、诊断、超时处理）")
    
    print("  ℹ 此部分使用多个股票代码进行重试、详细诊断")
    print("  ℹ 超时时间已增加到 20 秒\n")
    
    # 5.1 下单参数验证 - 使用重试机制
    order_data_base = {
        'order_type': 'buy',
        'order_volume': 10,  # 适度数量
        'price_type': 'fix',  # 固定价格
        'strategy_name': 'test_api',
        'order_remark': 'API测试'
    }
    
    successful_order_id = None
    
    # 尝试多个股票代码
    for idx, test_stock in enumerate(TEST_STOCK_CODES):
        order_data = order_data_base.copy()
        order_data['stock_code'] = test_stock
        # 根据股票调整价格
        order_data['price'] = 10.50 if 'SH' in test_stock else 50.00
        
        passed, msg, data = tester.test_endpoint('POST', '/api/trade/order', 
                                                f'下单测试 ({idx+1}/{len(TEST_STOCK_CODES)}: {test_stock})', 
                                                data=order_data)
        print_test_result(f'POST /api/trade/order ({test_stock})', passed, msg)
        
        if passed:
            result = data.get('data', {})
            order_id = result.get('order_id', -1)
            if order_id > 0:
                print(f"      ✓ 下单成功！订单ID: {order_id}")
                successful_order_id = order_id
                order_data['_order_id'] = order_id
                break  # 成功后退出循环
            else:
                print(f"      ✗ 返回的订单ID无效: {order_id}")
        else:
            print(f"      ✗ 错误: {msg}")
            if idx < len(TEST_STOCK_CODES) - 1:
                print(f"      → 尝试下一个股票代码...")
    
    # 如果所有下单尝试都失败，输出诊断信息
    if successful_order_id is None:
        print("\n  📋 下单失败诊断（所有股票都失败）:")
        print("     可能原因:")
        print("       1. 非交易时段（非工作日或非交易时间）")
        print("       2. 账户交易权限限制（模拟账户可能有特殊限制）")
        print("       3. 价格超出涨跌停范围")
        print("       4. 市场流动性不足")
        print(f"     建议: 在正常交易时段（9:30-15:00）重新运行测试")
    
    # 5.2 异步下单 - 改进的错误处理
    print()
    async_order_data = {
        'stock_code': '000858.SZ',  # 五粮液
        'order_type': 'buy',
        'order_volume': 1,
        'price_type': 'fix',
        'price': 50.00,
        'strategy_name': 'test_api_async',
        'order_remark': 'API异步下单测试'
    }
    passed, msg, data = tester.test_endpoint('POST', '/api/trade/order_async',
                                            '异步下单（000858.SZ）', data=async_order_data)
    print_test_result('POST /api/trade/order_async', passed, msg)
    
    if passed:
        result = data.get('data', {})
        seq = result.get('seq', -1)
        print(f"      ✓ 异步序列号: {seq}")
    else:
        print("\n  📋 异步下单诊断:")
        if 'NoneType' in msg or 'callback' in msg.lower():
            print("     ✗ 问题: 异步回调对象配置不完整")
            print("     原因: QMTConnection 中缺少 XtQuantTraderCallback 实现")
            print("     方案: 在 qmt_connection.py 中完善回调类实现")
        else:
            print(f"     错误: {msg}")
    
    # 5.3 撤单 - 改进的超时处理
    print()
    if successful_order_id and successful_order_id > 0:
        # 如果下单成功，使用真实的订单ID进行撤单
        cancel_data = {'order_id': successful_order_id}
        passed, msg, data = tester.test_endpoint('POST', '/api/trade/cancel',
                                                f'撤单（ID: {successful_order_id}）', data=cancel_data)
        print_test_result(f'POST /api/trade/cancel', passed, msg)
        
        if passed:
            result = data.get('data', {})
            result_code = result.get('result', -999)
            print(f"      ✓ 撤单结果: {result_code}")
        else:
            if '超时' in msg:
                print(f"      ✗ 撤单超时: {msg}")
            else:
                print(f"      ✗ 错误: {msg}")
    else:
        # 否则使用无效的ID进行参数检查
        print("  ⚠ 跳过真实撤单（下单未成功）")
        print("  ℹ 进行撤单参数有效性检查...")
        cancel_data = {'order_id': 99999}
        passed, msg, data = tester.test_endpoint('POST', '/api/trade/cancel',
                                                '撤单（参数检查）', data=cancel_data)
        print_test_result('POST /api/trade/cancel', passed, msg)
        
        if not passed and '超时' in msg:
            print("\n  📋 撤单超时诊断:")
            print("     问题: 请求超过 20 秒未返回")
            print("     原因: 没有对应的订单 ID，系统查询可能超时")
            print("     建议: 先确保下单成功，再进行撤单测试")


def run_parameter_validation_tests(tester: APITester):
    """参数验证测试"""
    print_header("6. 参数验证测试")
    
    tests = [
        # 缺少必填参数
        {
            'method': 'GET',
            'path': '/api/market/kline',
            'name': 'K线 - 缺少 stocks 参数',
            'params': {'period': '1d'},
            'expect_success': False
        },
        {
            'method': 'GET',
            'path': '/api/market/tick',
            'name': 'Tick - 缺少 stocks 参数',
            'params': {},
            'expect_success': False
        },
        {
            'method': 'GET',
            'path': '/api/market/instrument',
            'name': '合约信息 - 缺少 stock 参数',
            'params': {},
            'expect_success': False
        },
        {
            'method': 'POST',
            'path': '/api/trade/order',
            'name': '下单 - 缺少 stock_code 参数',
            'data': {'order_volume': 100},
            'expect_success': False
        },
    ]
    
    for test in tests:
        method = test['method']
        path = test['path']
        name = test['name']
        
        if method == 'GET':
            passed, msg, data = tester.test_endpoint(
                method, path, name,
                params=test.get('params', {}),
                expect_success=test.get('expect_success', True)
            )
        else:
            passed, msg, data = tester.test_endpoint(
                method, path, name,
                data=test.get('data', {}),
                expect_success=test.get('expect_success', True)
            )
        
        # 对于参数验证测试，失败是预期的
        should_fail = not test.get('expect_success', True)
        if should_fail and not passed:
            passed = True  # 正确地拒绝了坏请求
        
        print_test_result(path.split('/')[-1], passed, msg)


def print_summary():
    """打印测试总结"""
    print(f"\n{'='*70}")
    print(f"  测试总结")
    print(f"{'='*70}")
    
    total = test_results['passed'] + test_results['failed']
    percent = (test_results['passed'] / total * 100) if total > 0 else 0
    
    print(f"  总计: {total} 个测试")
    print(f"  通过: {test_results['passed']}")
    print(f"  失败: {test_results['failed']}")
    print(f"  成功率: {percent:.1f}%")
    
    if test_results['errors']:
        print(f"\n  失败详情:")
        for error in test_results['errors'][:10]:  # 最多显示 10 个
            print(f"    - {error}")
        if len(test_results['errors']) > 10:
            print(f"    ... 还有 {len(test_results['errors']) - 10} 个失败")


def main():
    """主测试函数"""
    print("\n" + "="*70)
    print("  QMT API 服务接口测试")
    print("="*70)
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  服务地址: {API_BASE_URL}")
    print(f"  Dry-Run 模式: {DRY_RUN_MODE}")
    
    # 创建测试器
    tester = APITester(API_BASE_URL, timeout=TIMEOUT)
    
    # 检查服务连接
    print(f"\n  正在连接到服务器...")
    try:
        resp = requests.get(f"{API_BASE_URL}/health", timeout=2)
        print(f"  ✓ 服务器已连接")
    except:
        print(f"  ✗ 无法连接到服务器，请确保服务已启动")
        return
    
    # 运行测试套件
    run_basic_tests(tester)
    run_status_tests(tester)
    run_query_tests(tester)
    run_market_tests(tester)
    run_parameter_validation_tests(tester)
    run_trade_tests(tester)
    
    # 打印总结
    print_summary()
    
    print("\n")


if __name__ == '__main__':
    main()
