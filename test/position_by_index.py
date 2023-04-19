import backtrader as bt # 导入 Backtrader
import backtrader.indicators as btind # 导入策略分析模块
import backtrader.feeds as btfeeds # 导入数据模块
import datetime
from sqlite_data import DataApi
import pandas as pd

# 创建策略
class TestStrategy(bt.Strategy):
    # 可选，设置回测的可变参数：如移动均线的周期
    # params = (
    #     (...,...), # 最后一个“,”最好别删！
    # )
    def log(self, txt, dt=None):
        '''可选，构建策略打印日志的函数：可用于打印订单记录或交易记录等'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        '''必选，初始化属性、计算指标等'''
        pass

    def notify_order(self, order):
        '''可选，打印订单信息'''
        pass

    def notify_trade(self, trade):
        '''可选，打印交易信息'''
        pass

    def next(self):
        '''必选，编写交易策略逻辑'''
        # sma = btind.SimpleMovingAverage(...) # 计算均线
        dt = self.datas[0].datetime.date(0)  # 获取当前的回测时间点
        print(dt)
        # 记录收盘价
        self.log('Close, %.2f' % self.data.close[0])
        self.order = self.buy(size=10)

    def next_open(self):
        # 取消之前未执行的订单
        if self.order:
            self.cancel(self.order)
        # 检查是否有持仓
        if not self.position:
            # 10日均线上穿5日均线，买入
            if self.crossover > 0:
                print('{} Send Buy, open {}'.format(self.data.datetime.date(),self.data.open[0]))
                self.order = self.buy(size=100) # 以下一日开盘价买入100股
        # # 10日均线下穿5日均线，卖出
        elif self.crossover < 0:
            self.order = self.close() # 平仓，以下一日开盘价卖出

def get_feeds(dataframe):
    dataframe['trade_date'] = pd.to_datetime(dataframe['trade_date'])
    date_list = dataframe['trade_date'].to_list()
    begin_date = date_list[0]  # 数据的起始日期
    end_date = date_list[-1]  # 数据的结束日期
    feeds = bt.feeds.PandasData(
        name='index000001SH', # 多股回测时用户区分数据对象
        dataname=dataframe,
        datetime=2,  # 日期行所在列
        open=4,  # 开盘价所在列
        high=5,  # 最高价所在列
        low=6,  # 最低价所在列
        close=3,  # 收盘价价所在列
        volume=10,  # 成交量所在列
        openinterest=-1,  # 无未平仓量列.(openinterest是期货交易使用的)
        fromdate=begin_date,  # 起始日
        todate=end_date
    )
    return feeds

if __name__ == '__main__':
    # 实例化 cerebro
    cerebro = bt.Cerebro()
    # 通过 feeds 读取数据
    data_api = DataApi()
    df = data_api.index_daily('000001.SH', '20230101', '20230201')
    datafeed = get_feeds(df)
    # 将数据传递给 “大脑”
    cerebro.adddata(datafeed, name='index000001SH')  # 通过name实现数据集与股票的一一对应

    # 设置经纪商
    # 初始资金 100,000,000
    cerebro.broker.setcash(100000000.0)
    # 佣金，双边各 0.0003
    cerebro.broker.setcommission(commission=0.0003)
    # 滑点：双边各 0.0001
    cerebro.broker.set_slippage_perc(perc=0.0001)
    # 设置单笔交易的数量
    # cerebro.addsizer(...)

    # 添加策略
    cerebro.addstrategy(TestStrategy)
    # 添加策略分析指标
    # cerebro.addanalyzer(...)
    # 添加观测器
    # cerebro.addobserver(...)
    # 启动回测
    cerebro.run()
    # 可视化回测结果
    cerebro.plot()
