#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mac 端交易客户端示例
====================
封装了 windows_service/api_server.py 暴露的全部接口，
涵盖 xtdata（行情）和 xttrader（交易/查询）所有功能。

使用方法：
  1. 修改 WINDOWS_HOST 为 Windows 实际 IP
  2. 运行: python mac_client_example.py
"""

import sys
import json
import time
from typing import List, Optional
from datetime import datetime

try:
    import requests
except ImportError:
    print("请先安装 requests: pip install requests")
    sys.exit(1)

# 从 Mac 端 config.py 读取连接配置
try:
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).parent.parent))
    from config import QMT_SERVICE_HOST, QMT_SERVICE_PORT, QMT_SERVICE_TOKEN
except ImportError:
    QMT_SERVICE_HOST  = '192.168.1.100'
    QMT_SERVICE_PORT  = 8080
    QMT_SERVICE_TOKEN = ''

# =============================================================================
# 配置
# =============================================================================

WINDOWS_HOST = QMT_SERVICE_HOST
WINDOWS_PORT = QMT_SERVICE_PORT
API_TOKEN    = QMT_SERVICE_TOKEN


# =============================================================================
# 客户端核心类
# =============================================================================

class QMTClient:
    """
    QMT REST API 客户端

    接口分组：
      service.*    服务控制（健康、状态、命令）
      query.*      账户/持仓/委托/成交 查询
      trade.*      下单/撤单
      market.*     行情数据（K线/Tick/合约/日历/板块/财务）
    """

    def __init__(self, host: str = WINDOWS_HOST, port: int = WINDOWS_PORT,
                 token: str = API_TOKEN, timeout: int = 10):
        self.base_url = f'http://{host}:{port}'
        self.timeout  = timeout
        self.session  = requests.Session()
        if token:
            self.session.headers['X-API-Token'] = token

    # ── 内部请求方法 ──

    def _get(self, path: str, params: dict = None) -> dict:
        try:
            r = self.session.get(f'{self.base_url}{path}',
                                 params=params, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _post(self, path: str, body: dict = None) -> dict:
        try:
            r = self.session.post(f'{self.base_url}{path}',
                                  json=body or {}, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # 服务控制
    # =========================================================================

    def health(self) -> dict:
        """健康检查"""
        return self._get('/health')

    def status(self) -> dict:
        """获取 Backtrader 侧汇总状态"""
        return self._get('/api/status')

    def start(self) -> dict:
        """启动交易策略"""
        return self._post('/api/command', {'command': 'start'})

    def stop(self) -> dict:
        """停止交易策略"""
        return self._post('/api/command', {'command': 'stop'})

    # =========================================================================
    # xttrader 查询接口
    # =========================================================================

    def query_asset(self) -> dict:
        """
        查询账户资产（直接调 xttrader.query_stock_asset）
        返回: cash, frozen_cash, market_value, total_asset
        """
        return self._get('/api/query/asset')

    def query_positions(self) -> dict:
        """
        查询持仓列表（直接调 xttrader.query_stock_positions）
        返回: [volume, can_use_volume, avg_price, market_value, ...]
        """
        return self._get('/api/query/positions')

    def query_orders(self, cancelable_only: bool = False) -> dict:
        """
        查询当日委托（直接调 xttrader.query_stock_orders）
        返回: [order_id, stock_code, order_type, order_volume, price, order_status, ...]
        """
        return self._get('/api/query/orders',
                         {'cancelable_only': str(cancelable_only).lower()})

    def query_trades(self) -> dict:
        """
        查询当日成交（直接调 xttrader.query_stock_trades）
        返回: [traded_id, stock_code, traded_price, traded_volume, traded_amount, ...]
        """
        return self._get('/api/query/trades')

    # =========================================================================
    # xttrader 交易接口
    # =========================================================================

    def order(self, stock_code: str, order_type: str, volume: int,
              price_type: str = 'latest', price: float = 0.0,
              strategy_name: str = 'mac_client',
              order_remark: str = '') -> dict:
        """
        同步下单（调 xttrader.order_stock）

        Args:
            stock_code:    合约代码，如 '511220.SH'
            order_type:    'buy' | 'sell'
            volume:        委托数量（股）
            price_type:    'latest'（最新价）| 'fix'（指定价）
            price:         price_type='fix' 时的委托价
            strategy_name: 策略名标记
            order_remark:  委托备注

        Returns:
            {'success': True, 'data': {'order_id': 12345}}
        """
        return self._post('/api/trade/order', {
            'stock_code':    stock_code,
            'order_type':    order_type,
            'order_volume':  volume,
            'price_type':    price_type,
            'price':         price,
            'strategy_name': strategy_name,
            'order_remark':  order_remark,
        })

    def order_async(self, stock_code: str, order_type: str, volume: int,
                    price_type: str = 'latest', price: float = 0.0,
                    strategy_name: str = 'mac_client',
                    order_remark: str = '') -> dict:
        """
        异步下单（调 xttrader.order_stock_async）
        返回 seq 序号，实际结果通过服务端 on_order_stock_async_response 回调处理。
        """
        return self._post('/api/trade/order_async', {
            'stock_code':    stock_code,
            'order_type':    order_type,
            'order_volume':  volume,
            'price_type':    price_type,
            'price':         price,
            'strategy_name': strategy_name,
            'order_remark':  order_remark,
        })

    def cancel(self, order_id: int) -> dict:
        """
        撤单（按订单编号，调 xttrader.cancel_order_stock）
        """
        return self._post('/api/trade/cancel', {'order_id': order_id})

    def cancel_by_sysid(self, order_sysid: str, market: str = 'SH') -> dict:
        """
        按柜台合同编号撤单（调 xttrader.cancel_order_stock_sysid）

        Args:
            order_sysid: 柜台合同编号
            market:      'SH' | 'SZ'
        """
        return self._post('/api/trade/cancel_sysid', {
            'market':      market,
            'order_sysid': order_sysid,
        })

    # =========================================================================
    # xtdata 行情接口
    # =========================================================================

    def kline(self, stocks: List[str], period: str = '1d',
              start: str = '', end: str = '',
              fields: List[str] = None,
              dividend_type: str = 'none',
              count: int = -1) -> dict:
        """
        K线历史数据（调 xtdata.get_market_data）

        Args:
            stocks:        合约代码列表，如 ['511220.SH', '159915.SZ']
            period:        K线周期: tick/1m/5m/15m/30m/1h/1d
            start:         开始时间，如 '20240101'
            end:           结束时间，如 '20241231'
            fields:        字段列表，空则返回全部
            dividend_type: 复权方式: none/front/back/front_ratio/back_ratio
            count:         数据条数，-1 不限制

        Returns:
            {stock_code: {field: [values...]}}
        """
        params = {
            'stocks': ','.join(stocks),
            'period': period,
            'start':  start,
            'end':    end,
            'fields': ','.join(fields) if fields else '',
            'dividend_type': dividend_type,
            'count':  count,
        }
        return self._get('/api/market/kline', params)

    def tick(self, stocks: List[str]) -> dict:
        """
        Tick 快照（调 xtdata.get_full_tick）

        Returns:
            {stock_code: {lastPrice, open, high, low, volume, bidPrice[5], askPrice[5], ...}}
        """
        return self._get('/api/market/tick', {'stocks': ','.join(stocks)})

    def instrument(self, stock: str) -> dict:
        """
        合约基础信息（调 xtdata.get_instrument_detail）

        Returns:
            {InstrumentName, PreClose, UpStopPrice, DownStopPrice,
             FloatVolume, TotalVolume, PriceTick, ...}
        """
        return self._get('/api/market/instrument', {'stock': stock})

    def instrument_type(self, stock: str) -> dict:
        """
        合约类型（调 xtdata.get_instrument_type）

        Returns:
            {'stock': '511220.SH', 'type': 'etf'}
        """
        return self._get('/api/market/instrument_type', {'stock': stock})

    def trading_calendar(self, market: str = 'SH',
                         start: str = '', end: str = '', count: int = -1) -> dict:
        """
        交易日历（调 xtdata.get_trading_dates）

        Returns:
            ['20240101', '20240102', ...]
        """
        return self._get('/api/market/calendar', {
            'market': market, 'start': start, 'end': end, 'count': count,
        })

    def holidays(self) -> dict:
        """
        节假日列表（调 xtdata.get_holidays）
        """
        return self._get('/api/market/holidays')

    def sector_list(self) -> dict:
        """
        板块列表（调 xtdata.get_sector_list）

        Returns:
            ['沪深300', '中证500', '上证50', ...]
        """
        return self._get('/api/market/sector')

    def sector_stocks(self, sector_name: str) -> dict:
        """
        板块成分股（调 xtdata.get_stock_list_in_sector）

        Args:
            sector_name: 板块名称，如 '沪深300'

        Returns:
            ['000001.SZ', '600000.SH', ...]
        """
        return self._get(f'/api/market/sector/{sector_name}')

    def index_weight(self, index_code: str) -> dict:
        """
        指数成分股权重（调 xtdata.get_index_weight）

        Args:
            index_code: 如 '000300.SH'（沪深300）

        Returns:
            {'000001.SZ': 0.0123, ...}
        """
        return self._get('/api/market/index_weight', {'index': index_code})

    def divid_factors(self, stock: str, start: str = '', end: str = '') -> dict:
        """
        除权数据（调 xtdata.get_divid_factors）

        Returns:
            [{'interest': 0.5, 'stockBonus': 0, ...}, ...]
        """
        return self._get('/api/market/divid', {
            'stock': stock, 'start': start, 'end': end,
        })

    def financial(self, stocks: List[str],
                  tables: List[str] = None,
                  start: str = '', end: str = '',
                  report_type: str = 'report_time') -> dict:
        """
        财务数据（调 xtdata.get_financial_data）

        Args:
            stocks:      合约代码列表
            tables:      报表类型: Income/Balance/CashFlow/Capital/
                         Holdernum/Top10holder/Pershareindex
            start/end:   报告期范围
            report_type: 'report_time'（报告期）| 'announce_time'（公告期）

        Returns:
            {table_name: [records...]}
        """
        return self._get('/api/market/financial', {
            'stocks':      ','.join(stocks),
            'tables':      ','.join(tables) if tables else '',
            'start':       start,
            'end':         end,
            'report_type': report_type,
        })

    def ipo_info(self, start: str, end: str) -> dict:
        """
        新股申购信息（调 xtdata.get_ipo_info）

        Returns:
            [{'stock_code': '...',  'ipo_date': '...', ...}, ...]
        """
        return self._get('/api/market/ipo', {'start': start, 'end': end})


# =============================================================================
# 格式化打印工具
# =============================================================================

def _ok(resp: dict) -> bool:
    return resp.get('success', False) or 'data' in resp or (
        isinstance(resp, dict) and 'error' not in resp and 'status' not in resp
    )


def print_resp(title: str, resp: dict, key: str = 'data'):
    print(f'\n{"─"*50}')
    print(f'▶ {title}')
    print(f'{"─"*50}')
    if 'error' in resp:
        print(f'  ❌ {resp["error"]}')
        return
    data = resp.get(key, resp)
    if isinstance(data, list):
        for i, item in enumerate(data[:5]):
            print(f'  [{i}] {item}')
        if len(data) > 5:
            print(f'  ... 共 {len(data)} 条')
    elif isinstance(data, dict):
        for k, v in list(data.items())[:10]:
            print(f'  {k}: {v}')
        if len(data) > 10:
            print(f'  ... 共 {len(data)} 项')
    else:
        print(f'  {data}')


# =============================================================================
# 交互式演示
# =============================================================================

MENU = """
╔══════════════════════════════════════╗
║   QMT Mac 客户端 — 功能菜单          ║
╠══════════════════════════════════════╣
║  服务控制                            ║
║   h  健康检查    s  汇总状态         ║
╠══════════════════════════════════════╣
║  账户查询（xttrader 直接查询）       ║
║   1  账户资产    2  持仓列表         ║
║   3  当日委托    4  当日成交         ║
╠══════════════════════════════════════╣
║  交易操作（xttrader 直接下单）       ║
║   5  下单示例    6  撤单示例         ║
╠══════════════════════════════════════╣
║  行情数据（xtdata）                  ║
║   7  K线数据     8  Tick 快照        ║
║   9  合约信息    0  交易日历         ║
║   a  板块列表    b  指数权重         ║
║   c  财务数据                        ║
╠══════════════════════════════════════╣
║   q  退出                            ║
╚══════════════════════════════════════╝
"""


def demo(client: QMTClient):
    """交互式演示"""
    print(MENU)

    while True:
        try:
            cmd = input('命令: ').strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if cmd == 'q':
            break
        elif cmd == 'h':
            print_resp('健康检查', client.health(), key='status')
        elif cmd == 's':
            print_resp('汇总状态', client.status())
        elif cmd == '1':
            print_resp('账户资产', client.query_asset())
        elif cmd == '2':
            print_resp('持仓列表', client.query_positions())
        elif cmd == '3':
            print_resp('当日委托', client.query_orders())
        elif cmd == '4':
            print_resp('当日成交', client.query_trades())
        elif cmd == '5':
            # 示例：以最新价买入 511220.SH 100 股
            r = client.order('511220.SH', 'buy', 100)
            print_resp('下单结果', r)
        elif cmd == '6':
            oid = input('输入 order_id: ').strip()
            if oid.isdigit():
                print_resp('撤单结果', client.cancel(int(oid)))
        elif cmd == '7':
            r = client.kline(['511220.SH', '159915.SZ'],
                             period='1d', start='20240101', end='20241231',
                             fields=['open', 'close', 'volume'])
            print_resp('K线数据', r)
        elif cmd == '8':
            r = client.tick(['511220.SH'])
            print_resp('Tick 快照', r)
        elif cmd == '9':
            r = client.instrument('511220.SH')
            print_resp('合约信息', r)
        elif cmd == '0':
            r = client.trading_calendar('SH', start='20240101', end='20241231')
            print_resp('交易日历', r)
        elif cmd == 'a':
            print_resp('板块列表', client.sector_list())
        elif cmd == 'b':
            r = client.index_weight('000300.SH')
            print_resp('沪深300 成分权重', r)
        elif cmd == 'c':
            r = client.financial(
                ['600000.SH'], tables=['Income'],
                start='20230101', end='20231231',
            )
            print_resp('财务数据', r)
        else:
            print('  未知命令，输入 q 退出')


# =============================================================================
# 主函数
# =============================================================================

def main():
    print('=' * 60)
    print('QMT Mac 端客户端')
    print(f'目标: {WINDOWS_HOST}:{WINDOWS_PORT}')
    print('=' * 60)

    client = QMTClient()

    # 连接检查
    h = client.health()
    if 'error' in h:
        print(f'❌ 无法连接: {h["error"]}')
        print('\n请检查：')
        print('  1. Windows 服务是否已启动（run_service.py）')
        print('  2. IP/端口是否正确（当前: '
              f'{WINDOWS_HOST}:{WINDOWS_PORT}）')
        print('  3. 两台机器是否在同一网络')
        return

    running = h.get('running', False)
    conn    = h.get('connected', False)
    print(f'服务状态: {"🟢 运行中" if running else "🔴 未运行"}')
    print(f'QMT连接:  {"🟢 已连接" if conn else "🔴 未连接"}')

    demo(client)
    print('退出')


if __name__ == '__main__':
    main()
