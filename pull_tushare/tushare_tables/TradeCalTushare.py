import pandas as pd
import sqlite3
import datetime
import pendulum

from config import tushare_api
from models.table_models import *
from models.api import *


class TradeCalTushare:
    def __init__(self):
        self.from_api = tushare_api.trade_cal
        self.to_table = TradeCal

    def down_write(self):
        """2.交易日历trade_cal"""
        # 交易所SSE上交所, SZSE深交所, CFFEX中金所, SHFE上期所, CZCE郑商所, DCE大商所, INE上能源
        df = pd.DataFrame()
        for i in ['SSE', 'SZSE', 'CFFEX', 'SHFE', 'CZCE', 'DCE', 'INE']:
            df2 = tushare_api.trade_cal(exchange=i)
            df = pd.concat([df, df2], axis=0)
        print(df)
        def to_datetime(x):
            try:
                x = pendulum.parse(x)
            except:
                x = None
            return x
        df['cal_date'] = df.apply(lambda x: to_datetime(x['cal_date']), axis=1)
        df['pretrade_date'] = df.apply(lambda x: to_datetime(x['pretrade_date']), axis=1)
        df['exchange_cal_date'] = df.apply(lambda x: x['exchange'] + str(x['cal_date']), axis=1)
        print(df)
        delete_magic = delete(TradeCal)
        data_api.delete_data(delete_magic)
        print('删除trade_cal')
        try:
            data_api.write(df, TradeCal)
            print('trade_cal下载成功')
        except sqlite3.IntegrityError:
            print('trade_cal已经存在或%s' % sqlite3.IntegrityError)

    def pull(self):
        # 取下日历日期最后一天，上次更新到n年12月30日
        query_magic = session.query(TradeCal.cal_date).filter(TradeCal.exchange=='SSE').limit(1)
        df = data_api.query(query_magic)
        if len(df)==0:
            self.down_write()
        else:
            date = df['cal_date'][0]
        # 是否过了n年11月31，如果过了每天尝试更新下一年（n = 日历最后一天的年份）
        today = datetime.datetime.today()
        if today > datetime.datetime(year=date.year, month=11, day=30):
            self.down_write()
        else:
            print(f'{self.to_table.__tablename__}日历已经更新到{date}, 不需要再更新')



if __name__ == "__main__":
    TradeCalTushare().pull()
