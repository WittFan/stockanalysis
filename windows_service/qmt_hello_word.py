# coding=utf-8

import os
import sys

# 打印当前路径
print("当前工作目录:", os.getcwd())
print("Python 路径:", sys.path)

# 将项目根目录添加到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print("已将项目根目录添加到 Python 路径:", project_root)

from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant.xtdata import get_holidays, download_history_data
from xtquant import xtdata
import time


print("demo test")
# path为mini qmt客户端安装目录下userdata_mini路径
path = r'C:/国金QMT交易端模拟/userdata_mini'
# session_id为会话编号，策略使用方对于不同的Python策略需要使用不同的会话编号
session_id = int(time.time())
xt_trader = XtQuantTrader(path, session_id)
# 开启主动请求接口的专用线程 开启后在on_stock_xxx回调函数里调用XtQuantTrader.query_xxx函数不会卡住回调线程，但是查询和推送的数据在时序上会变得不确定
# 详见: http://docs.thinktrader.net/vip/pages/ee0e9b/#开启主动请求接口的专用线程
xt_trader.set_relaxed_response_order_enabled(True)
# 创建资金账号为1000000365的证券账号对象
acc = StockAccount('55003046')
# StockAccount可以用第二个参数指定账号类型，如沪港通传'HUGANGTONG'，深港通传'SHENGANGTONG'
# acc = StockAccount('1000000365','STOCK')

# 启动交易线程
xt_trader.start()
# 建立交易连接，返回0表示连接成功
connect_result = xt_trader.connect()
if connect_result != 0:
    import sys
    sys.exit('链接失败，程序即将退出 %d' % connect_result)
else:
    print(connect_result)

# 查询当日所有的持仓
print("query positions:")
positions = xt_trader.query_stock_positions(acc)
print("positions:", positions)
if len(positions) != 0:
    print("last position:")
    print("{0} {1} {2}".format(positions[-1].account_id, positions[-1].stock_code, positions[-1].volume))

# 查询证券资产
print("query asset:")
asset = xt_trader.query_stock_asset(acc)
if asset:
    print("asset:")
    print("cash {0}".format(asset.cash))

stock_code = '600519.SH'  # 例如,贵州茅台的股票代码
start_date = '20240301'  # 开始日期
end_date = '20240330'   # 结束日期
period = '1d'

print(get_holidays())
# xtdata.download_history_data(stock_code='600519.SH', period='1d', start_time=start_date, end_time=end_date)
data = xtdata.get_market_data(field_list=[], stock_list=['600519.SH',], period='1d', start_time=start_date, end_time=end_date)
print(data['open'])

def on_data(datas):
    for stock_code in datas:
        print(stock_code, datas[stock_code])
def on_stock_data():
    print("######subscribe_whole_quote######")
    subscribe_result = xtdata.subscribe_whole_quote(['600519.SH', '600520.SH'], callback=on_data)
    print(subscribe_result)
# on_stock_data()

def on_single_stock_data(data):
    print('单只股票:', data)
def single_stock_data():
    print("######  订阅单只股票  ######")
    subscribe_result = xtdata.subscribe_quote('600519.SH', period='tick', start_time='', end_time='', count=0,
    callback=on_single_stock_data)
    print(subscribe_result)
    print(xtdata.unsubscribe_quote(subscribe_result))

