from config import tushare_api
from models import *
from models.api import *
import pandas as pd
import sqlite3

class TradeCalTushare:
    def __init__(self):
        self.from_api = tushare_api.trade_cal
        self.to_table = TradeCal
        # self.__name__ = 'trade_cal'

    def get_last_day(self):
        """读取本地数据库最新日期的数据"""
        # 从数据库的update_date_record中查询更新的最后一个日期
        conn = sqlite3.connect(self.data_api.database)
        c = conn.cursor()
        c.execute(self.last_day_sql)
        conn.commit()
        date = c.fetchall()
        if date == []:
            return None
        date = date[0][0]
        conn.close()
        return date

    def pull(self):
        """2.交易日历trade_cal"""
        # 交易所SSE上交所, SZSE深交所, CFFEX中金所, SHFE上期所, CZCE郑商所, DCE大商所, INE上能源
        df = pd.DataFrame()
        for i in ['SSE', 'SZSE', 'CFFEX', 'SHFE', 'CZCE', 'DCE', 'INE']:
            df2 = tushare_api.trade_cal(exchange=i)
            df = pd.concat([df, df2], axis=0)
        df['exchange_cal_date'] = df.apply(lambda x: x['exchange'] + str(x['cal_date']), axis=1)
        delete_magic = delete(TradeCal)
        data_api.delete_data(delete_magic)
        print('删除trade_cal')
        try:
            data_api.write(df, TradeCal)
            print('trade_cal下载成功')
        except sqlite3.IntegrityError:
            print('trade_cal已经存在或%s' % sqlite3.IntegrityError)