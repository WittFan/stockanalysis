from utils import to_datetime
from utils import today_todatetime

import pandas as pd
import numpy as np
from datetime import datetime
# import duckdb
from orm_models.api import data_api
from orm_models.table_models import *

from tqdm import tqdm
import abc
from datafeed.expr import calc_expr


class Dataloader:

    def __init__(self, path, symbols, start_date='20100101', end_date=datetime.now().strftime('%Y%m%d')):
        self.symbols = symbols
        self.path = path
        self.start_date = to_datetime(start_date)
        if not end_date or end_date == '':
            end_date = today_todatetime()
        self.end_date = to_datetime(end_date)

    @abc.abstractmethod
    def _load_dfs(self):
        pass

    def _concat_dfs(self, dfs: list):
        df = pd.concat(dfs)
        df.sort_index(inplace=True)
        return df

    def _reset_index(self, df: pd.DataFrame):
        trade_calendar = list(set(df.index))
        trade_calendar.sort()

        def _ffill_df(sub_df: pd.DataFrame):
            df_new = sub_df.reindex(trade_calendar, method='ffill')
            return df_new

        df = df.groupby('symbol', group_keys=False).apply(lambda sub_df: _ffill_df(sub_df))
        return df

    def load(self, fields=None, names=None):
        dfs = self._load_dfs()
        # df = self._reset_index(df)

        if not fields or not names or len(fields) != len(names):
            return self._concat_dfs(dfs)
        else:
            # 截面rank需要
            dfs_expr = []
            for df in tqdm(dfs):
                cols = []
                count = 0
                for field, name in tqdm(zip(fields, names)):
                    se = calc_expr(df, field)
                    count += 1
                    if count < 10:
                        df[name] = se
                    else:
                        se.name = name
                        cols.append(se)
                if len(cols):
                    df_cols = pd.concat(cols, axis=1)
                    df = pd.concat([df, df_cols], axis=1)
                dfs_expr.append(df)
            df_all = self._concat_dfs(dfs_expr)
            # todo 如果需要支持截面rank，逻辑加在这里
            # todo groupby('date').rank(pct=True)
            return df_all

class Duckdbloader(Dataloader):
    """ 将数据库中的数据转换成backtrader的datafeed可以使用的格式，数据库使用的是sqlite，名字暂且用duckdb吧 """

    def __init__(self, path, symbols, columns, start_date='20100101',
                 end_date=datetime.now().strftime('%Y%m%d'), folder='/*'):
        """ 标的代码，列名，开始时间，结束时间"""
        super().__init__(None, symbols, start_date, end_date)
        self.path = path
        self.columns = columns
        self.columns.extend(['symbol', 'date'])
        self.folder = folder

    @staticmethod
    def adj_price(df):
        """ 计算OHLC的复权价格
        # fund_adj数据与fund_daily数据行数不一致，所以tushare复权数据用不了。
        # 复权分为前复权、后复权：前复权保持当前价格不变，对历史价格进行增减，使得股价连续。后复权正好相反，保持第一个价格不变，调整后面的价格。前复权是行情软件默认模式，因为它很适合用来看盘。后复权适合用来对历史回测和计算收益率。
        # 前复权由于以下2个缺点，使得其不适合用来回测：（1）历史数值是时变的：每次发生派息等除权事件时，历史数值都会根据当前的股价而调整。换句话说，每次发生除权事件后，历史数值都是不一样的；（2）股价可能为负：对于持续分红的公司，其前复权价格可能为负。
        # 使用数据的理念（不单单是复权数据）：只使用第三方提供的像开高低收、成交量等一手数据。其次，对于需要二次加工的数据，如市盈率、ROE等指标，自己算一遍。因为回测对数据的要求是非常严格的，而第三方（即使是大机构）的数据质量参差不齐，可能会因为计算公式的细微差别造成较大的误差，可能引入未来函数，更可能产生某些问题直达实盘才会发现。
        # 1.用前收盘价计算后复权。前收盘价是前一交易日的收盘价格，是交易所帮我们算好的除权后的价格，用当日收盘价除前收盘价就可以得到真实收益率。
        # df['复权因子'] = (df['收盘价'] / df['前收盘价']).cumprod()
        # df['收盘价_复权'] = df['复权因子'] * (df.iloc[0]['收盘价'] / df.iloc[0]['复权因子'])
        # df['开盘价_复权'] = df['开盘价'] / df['收盘价'] * df['收盘价_复权']
        # df['最高价_复权'] = df['最高价'] / df['收盘价'] * df['收盘价_复权']
        # df['最低价_复权'] = df['最低价'] / df['收盘价'] * df['收盘价_复权']
        # 2.tushare复权参考
        # 后复权 = 当日最新价 × 当日复权因子
        # 前复权 = 当日最新价 ÷ 最新复权因子
        """
        df.sort_values(by='trade_date', ascending=True)
        df['adj'] = (df['close'] / df['pre_close']).cumprod()
        df['close_after_adj'] = df['adj'] * (df.iloc[0]['close'] / df.iloc[0]['adj'])
        df['open_after_adj'] = df['open'] / df['close'] * df['close_after_adj']
        df['high_after_adj'] = df['high'] / df['close'] * df['close_after_adj']
        df['low_after_adj'] = df['low'] / df['close'] * df['close_after_adj']
        return df

    @staticmethod
    def drop_and_rename(df_adj):
        """ 重命名后，只保留复权后的OHLC、volume、symbol、date"""
        drop_list = ['ts_code_trade_date', 'pre_close', 'close', 'open', 'high', 'low', 'change', 'pct_chg', 'amount',
                     'adj']
        df_adj.drop(columns=drop_list, inplace=True)
        rename_list = {'ts_code': 'symbol', 'trade_date': 'date',
                       'close_after_adj': 'close', 'open_after_adj': 'open', 'high_after_adj': 'high',
                       'low_after_adj': 'low',
                       'vol': 'volume'}
        df_adj.rename(columns=rename_list, inplace=True)
        df = df_adj
        return df

    def cal_adj_price(self, df):
        """ 计算复权价格，返回 symbol、date、OHLC、volume """
        dfs = [df for _, df in df.groupby('ts_code')]
        dfs_list = []
        for df in dfs:
            df = self.adj_price(df)
            dfs_list.append(df)
        df = pd.concat(dfs_list)
        df = self.drop_and_rename(df)  # 只保留symbol、date、OHLC、volume
        return df

    def _load_dfs(self):
        # to do 将fund_daily、daily、index_daily表里的价格进行后复权
        df = pd.DataFrame()
        for table_model in [Daily, IndexDaily, FundDaily]: # 逐个表查询
            # read_symbols已经按照trade_date排序了。
            df2 = data_api.read_symbols(table_model, symbols=self.symbols, fields=None,
                                       start_datetime=self.start_date, end_datetime=self.end_date)
            if len(df2):
                df = pd.concat([df, df2], axis=0)
        df = self.cal_adj_price(df)
        df.set_index('date', inplace=True)  # 将date设置为索引
        df.sort_index(inplace=True, ascending=True) # 按照date排序
        dfs = [df for _, df in df.groupby('symbol')]
        return dfs


if __name__ == '__main__':
    from datafeed.dataloader import Duckdbloader
    test_id = 2
    # from config import DATA_DIR_CSVS

    # 证券代码
    symbols =  ["510300.SH", "159915.SZ", "511220.SH", "518880.SH", "513100.SH",  # 场内基金
               '688502.SH', '688080.SH']           # 股票
    path = ""
    columns = ['open', 'high', 'low', 'close', 'volume']
    start_date = '19910101'
    end_date = '20231104'
    folder = '/'

    # 测试read_symbols
    if test_id == 1:
        df = data_api.read_symbols(Daily, symbols=symbols, fields=None)
        df1 = df.apply(lambda x: type(x['trade_date']), axis=1)
        print(df1)

    if test_id == 2:
        loader = Duckdbloader(path=path, symbols=symbols, columns=columns, start_date=start_date, end_date=end_date, folder=folder)
        # fields = []
        # names = []
        fields = ["slope_pair(high,low,18)", ]
        names = [ "rsrs",]
        # fields = ["roc(close,20)", "slope_pair(high,low,18)", ]
        # names = [ "roc_20", "rsrs",]
        import datetime
        #######  开始 #######
        start_process = datetime.datetime.now()

        df = loader.load(fields=fields, names=names)
        df.dropna(inplace=True)
        print(df)
        df.to_excel('loader_df.xlsx')
        #######  结束 ######
        end_process = datetime.datetime.now()
        print(end_process-start_process)

    if test_id == 3:
        loader = Duckdbloader(path=path, symbols=symbols, columns=columns, start_date=start_date, end_date=end_date,
                              folder=folder)
        loader.data_adj()
