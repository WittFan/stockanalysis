import sqlite3
import datetime
import pendulum

from config import tushare_api
from models.table_models import *
from models.api import *


class IndexBasicTushare:
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
        data_api.delete_data(delete(TradeCal))
        data_api.delete_data(delete(TradeWeek))
        data_api.delete_data(delete(TradeMonth))
        print('删除trade_cal、trade_week、trade_month')
        try:
            data_api.write(df, TradeCal)
            print('trade_cal下载成功')
            self.write_TradeWeek()
            self.write_TradeMonth()
        except sqlite3.IntegrityError:
            print('trade_cal已经存在或%s' % sqlite3.IntegrityError)

    def write_TradeWeek(self):
        # 交易日历上每周最后一个交易日
        # SSE开始于19901219 SZSE开始于19910703，因此只需要SSE。返回的交易日历仅仅是从开始时间到今年最后一天，扣除节假日。
        trade_cal = pd.DataFrame(data_api.query(session.query(TradeCal).filter(TradeCal.exchange=='SSE').filter(TradeCal.is_open=='1'))['cal_date'][::-1])
        trade_cal['week_info'] = trade_cal.apply(lambda x: x['cal_date'].date().isocalendar(), axis=1)
        trade_cal['year'] = trade_cal.apply(lambda x: x['week_info'][0], axis=1)
        trade_cal['week'] = trade_cal.apply(lambda x: x['week_info'][1], axis=1)
        trade_cal['day'] = trade_cal.apply(lambda x: x['week_info'][2], axis=1)
        df = trade_cal.groupby(['year', 'week']).apply(lambda x: x[x['day'] == x['day'].max()])
        df['pretrade_date'] = df['cal_date'].shift()
        df['exchange'] = 'SSE'
        df = df.drop(columns=['week_info', 'year', 'week', 'day'])
        try:
            data_api.write(df, TradeWeek)
            print('trade_week下载成功')
        except sqlite3.IntegrityError:
            print('trade_week已经存在或%s' % sqlite3.IntegrityError)

    def write_TradeMonth(self):
        # 交易日历上每周最后一个交易日
        # SSE开始于19901219 SZSE开始于19910703，因此只需要SSE。返回的交易日历仅仅是从开始时间到今年最后一天，扣除节假日。
        trade_cal = pd.DataFrame(data_api.query(session.query(TradeCal).filter(TradeCal.exchange=='SSE').filter(TradeCal.is_open=='1'))['cal_date'][::-1])
        trade_cal['month_info'] = trade_cal.apply(lambda x: x['cal_date'].date(), axis=1)
        trade_cal['year'] = trade_cal.apply(lambda x: x['month_info'].year, axis=1)
        trade_cal['month'] = trade_cal.apply(lambda x: x['month_info'].month, axis=1)
        trade_cal['day'] = trade_cal.apply(lambda x: x['month_info'].day, axis=1)
        df = trade_cal.groupby(['year', 'month']).apply(lambda x: x[x['day'] == x['day'].max()])
        df['pretrade_date'] = df['cal_date'].shift()
        df['exchange'] = 'SSE'
        df = df.drop(columns=['month_info', 'year', 'month', 'day'])
        try:
            data_api.write(df, TradeMonth)
            print('trade_month下载成功')
        except sqlite3.IntegrityError:
            print('trade_month已经存在或%s' % sqlite3.IntegrityError)

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

    def pull_index_basic_all(self):
        """6.指数基本信息index_basic"""
        df = self.pro.index_basic(fields=["ts_code", "name", "fullname", "market", "publisher", "index_type", "category",
                                     "base_date", "base_point", "list_date", "weight_rule", "desc", "exp_date"])
        from sqlite_data import delete_table
        delete_table('index_basic')
        print('删除index_basic')
        try:
            sqlite_data.write(df, 'index_basic')
            print('index_basic下载成功')
        except sqlite3.IntegrityError:
            print('index_basic已经存在或%s' % sqlite3.IntegrityError)


if __name__ == "__main__":
    IndexBasicTushare().down_write()
