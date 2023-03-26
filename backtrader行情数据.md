## 将dataframe对象加载到 bt.feeds.PandasData

生成回测的行情数据对象。
范例：
数据来源 akshare

```python
import akshare as ak
获取历史行情数据
stock_zh_a_hist_df = ak.stock_zh_a_hist(
    symbol=g_stock_code,  # 股票代码
    period="daily",  # {'daily', 'weekly', 'monthly'}
    adjust='qfq'  # qfq:前复权；hfq:后复权
)
print(stock_zh_a_hist_df[:5])  # 查看前5行数据
out:
日期     开盘     收盘     最高   最低     成交量    成交额      振幅  \
0 2021-08-18  14.50  18.00  19.88  14.50  780346  1.265741e+09  130.27   
1 2021-08-19  17.00  15.42  17.48  15.36  629396  1.026323e+09   11.78   
2 2021-08-20  15.16  14.81  16.48  14.71  486654  7.591273e+08   11.48   
3 2021-08-23  14.20  15.62  16.21  13.98  445712  6.849244e+08   15.06   
4 2021-08-24  15.27  15.51  16.20  14.82  445999  6.878077e+08    8.83
  涨跌幅    涨跌额    换手率  
0  335.84  13.87  88.95  
1  -14.33  -2.58  71.74  
2   -3.96  -0.61  55.47  
3    5.47   0.81  50.81  
4   -0.70  -0.11  50.84
```

下面定义一个函数，接收dataframe对象，生成一个行情数据对象

```python
def get_feeds(dataframe):
    dataframe['日期'] = dataframe['日期'].apply(str)
    dataframe['日期'] = pd.to_datetime(dataframe['日期'])
    date_list = dataframe['日期'].to_list()

    begin_date = datetime.strptime(str(date_list[0]), "%Y-%m-%d %H:%M:%S")  # 数据的起始日期
    end_date = datetime.strptime(str(date_list[-1]), "%Y-%m-%d %H:%M:%S")  # 数据的起始日期

    feeds = bt.feeds.PandasData(
    	  name='数据名称', # 多股回测时用户区分数据对象
        dataname=dataframe,
        datetime=0,  # 日期行所在列
        open=1,  # 开盘价所在列
        high=3,  # 最高价所在列
        low=4,  # 最低价所在列
        close=2,  # 收盘价价所在列
        volume=5,  # 成交量所在列
        openinterest=-1,  # 无未平仓量列.(openinterest是期货交易使用的)
        fromdate=begin_date,  # 起始日
        todate=end_date
    )
    return feeds
```

## PandasData拓展line

可以看到原始的 bt.feeds.PandasData使用的line为：datetime、open、high、low、close、volume

希望将行情数据中的 换手率 加入行情数据需要如下操作：

```python
# 自定义数据类，继承PandasData
from backtrader.feeds import PandasData
class PandasData_Change(PandasData):
    '''增加 换手率线的 数据源类'''
    # 增加pe线
    lines = ('change', )
    # 默认第8列
    params = (
        ('change', 8),
    )
```

将数据注入自定义的数据类，我们修改了一下生成行情数据对象的方法，增加了 change 参数，并定义为第10列数据：

```python
def get_feeds(dataframe):
    dataframe['日期'] = dataframe['日期'].apply(str)
    dataframe['日期'] = pd.to_datetime(dataframe['日期'])
    date_list = dataframe['日期'].to_list()

    begin_date = datetime.strptime(str(date_list[0]), "%Y-%m-%d %H:%M:%S")  # 数据的起始日期
    end_date = datetime.strptime(str(date_list[-1]), "%Y-%m-%d %H:%M:%S")  # 数据的起始日期

    feeds = PandasData_Change(
        dataname=dataframe,
        datetime=0,  # 日期行所在列
        open=1,  # 开盘价所在列
        high=3,  # 最高价所在列
        low=4,  # 最低价所在列
        close=2,  # 收盘价价所在列
        volume=5,  # 成交量所在列
        openinterest=-1,  # 无未平仓量列.(openinterest是期货交易使用的)
        fromdate=begin_date,  # 起始日
        todate=end_date,
        change=10  # 新定义 换手率线 的索引
    )
    return feeds
```

运行策略查看 新的line可以像这样获取

```python
class SmaCross(bt.Strategy):

    def __init__(self):

        '''获取 换手率线'''
        change_line = self.data.change
        lg.info(
            change_line
        )

    def next(self):
        pass

cerebro = bt.Cerebro()
cerebro.adddata(feed)
cerebro.addstrategy(SmaCross)
cerebro.broker.setcash(10000)
cerebro.run()
```

## 使用pandasDirectData

后期新版增加，作用是提高效率
使用pandasDirectData 需要遵循一下规则：
1、dataframe的日期时间列要设为索引列
2、dataframe里不能有字符串列，如：股票代号
3、bt.PandasDirectData(…)时，不能设置datatime列

继续使用上面的行情数据，修改生成行情数据对象的方法：
1、重新索引 dataframe.set_index()
2、删除字符串列 dataframe.drop() ，这里没有

```python
def get_feeds(dataframe):
    dataframe['日期'] = dataframe['日期'].apply(str)
    dataframe['日期'] = pd.to_datetime(dataframe['日期'])
    date_list = dataframe['日期'].to_list()
		# 增加重新索引
    dataframe = dataframe.set_index(keys=['日期'], inplace=True)

    begin_date = datetime.strptime(str(date_list[0]), "%Y-%m-%d %H:%M:%S")  # 数据的起始日期
    end_date = datetime.strptime(str(date_list[-1]), "%Y-%m-%d %H:%M:%S")  # 数据的起始日期

    feeds = PandasDirectData(
        dataname=dataframe,
        open=1-1,  # 开盘价所在列
        high=3-1,  # 最高价所在列
        low=4-1,  # 最低价所在列
        close=2-1,  # 收盘价价所在列
        volume=5-1,  # 成交量所在列
        openinterest=-1,  # 无未平仓量列.(openinterest是期货交易使用的)
        fromdate=begin_date,  # 起始日
        todate=end_date,
        change=10-1  # 新定义 换手率线 的索引
    )
    return feeds
```

