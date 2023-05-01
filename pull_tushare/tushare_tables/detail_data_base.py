"""  明细数据下载到本地的基类  """
import sqlite3
import datetime

from config import tushare_api
from models.table_models import *
from models.api import *
from utils import to_datetime


class DetailDataBase:
    def __init__(self):
        self.from_api = tushare_api.daily
        self.to_table = Daily
        self.fields = ["ts_code", "name", "fullname", "market", "publisher", "index_type", "category",
                    "base_date", "base_point", "list_date", "weight_rule", "desc", "exp_date"]
        self.to_datetime_list = ['list_date', 'exp_date']
        self.frequency = 'monthly'

    def get_record_cal(self):
        # 股票的交易日历
        # SSE开始于19901219 SZSE开始于19910703，因此只需要SSE。返回的交易日历仅仅是从开始时间到今年最后一天，扣除节假日。
        query_magic = session.query(TradeCal).filter(TradeCal.exchange=='SSE').filter(TradeCal.is_open == '1')
        trade_cal = data_api.query(query_magic)['cal_date'][::-1]
        trade_cal = list(trade_cal)
        return trade_cal

    def get_last_date(self):
        """ 读取本地数据库最新日期的数据 """
        # 取下更细记录上数据标记日期，上次更新到n月m日。
        query_magic = session.query(UpdateRecord.data_datetime).filter(UpdateRecord.table==self.to_table.__tablename__).limit(1)
        df_table = data_api.query(query_magic)
        if len(df_table) == 0:
            date = datetime.datetime(year=1990, month=1, day=1)
        else:
            date = df_table['data_datetime'][0]
        return date

    def get_end_date(self):
        # end_date为今日，若今日不在日历里，则向前取最近的一个
        end_date_timestamp = self.today
        self.end_date = end_date_timestamp.strftime("%Y%m%d")
        while True:
            if self.end_date in self.record_cal:
                return
            else:
                end_date_timestamp = end_date_timestamp - datetime.timedelta(days=1)
                self.end_date = end_date_timestamp.strftime("%Y%m%d")

    def get_frequency_date(self):
        # date是n年m月l日，全年第k周
        # yearly:  是否过了n年11月30，如果过了每次尝试更新下一年（n = 日历最后一天的年份）
        # monthly: 是否过了m+1月25，如果过了每天尝试更新m+1月
        # weekly:  是否过了第k+1周周五，如果过了每天尝试更新k+1周
        # dayly:   每天更新
        # 是否过了n+1月25，如果过了每天尝试更新n+1月
        if self.frequency == 'yearly':
            return datetime.datetime(year=self.last_date.year, month=11, day=25)
        elif self.frequency == 'monthly':
            return datetime.datetime(year=self.last_date.year, month=self.last_date.month+1, day=25)
        elif self.frequency == 'weekly':
            day = self.last_date.isocalendar()[2] # 周几
            if day >= 5:
                day_number = 5 - day + 7
            else:
                day_number = 5 - day
            return self.last_date + datetime.timedelta(days=day_number)
        elif self.frequency == 'dayly':
            return self.last_date

    def get_update_date_list(self):
        ##########  赋值下载的开始日期、结束日期  ###################
        if self.last_day is None:
            start_date = self.record_cal[0]
            self.last_day = self.record_cal[0] #为了在下一个if判断有数值，该变量必须有数值
        else:
            print('上一次更新到', self.last_day)
            start_date = self.record_cal[self.record_cal.index(self.last_day)+1]  # 在数据库的最后一个日期再往后移动一天
        # 计算需要更新的百分比
        update_percent = round(self.record_cal.index(self.last_day) / self.record_cal.index(self.end_date) * 100, 2)
        print(f'表{self.table_name}已更新： {update_percent}%，', '下一步', start_date, self.end_date)
        # 准备下载日期区间[start_date, end_date]
        update_date_list = self.record_cal[self.record_cal.index(start_date):self.record_cal.index(self.end_date)+1]
        return update_date_list

    def get_data_from_tushare(self, date):
        df = self.tushare_api.query(self.table_name, trade_date=date)
        return df

    def get_data_from_tushare_wait(self, date):
        # 如果接口有限制则等待5秒，直到可以继续调用
        while True:
            try:
                df = self.get_data_from_tushare(date)
                break
            except Exception as e:
                print(f'在下载表{self.table_name}{date}时等待20秒', e)
                time.sleep(20)
        return df

    def set_primary_key(self, df):
        # 添加primary key
        df['ts_code_trade_date'] = df.apply(lambda x: x['ts_code'] + str(x['trade_date']), axis=1)
        df = df.drop_duplicates('ts_code_trade_date')
        return df

    def add_update_date_record(self, df, date):
        # 标记已更新日期到ts_code = update_date_record 数据上
        df2 = pd.DataFrame({'trade_date': [date]})
        df2['ts_code'] = 'update_date_record'
        df2 = self.set_primary_key(df2)
        df = pd.concat([df, df2], axis=0)
        return df

    def process_data(self, df, date):
        # 判断date日期下是否有数据，有数据则添加primary key，添加更新记录
        if len(df) > 0:
            df = self.set_primary_key(df)
            print(f'表{self.table_name}，日期{date}，下载处理数据成功，数据长度{len(df)}')
            df = self.add_update_date_record(df, date)
        return df

    def write_sqlite_data(self, df, date):
        # 将下载的数据插入数据库
        try:
            sqlite_data.write(df, self.table_name)
            print(f'表{self.table_name}，日期{date}，入库数据成功   ，数据长度{len(df)}')
        except sqlite3.IntegrityError:
            print('表{table_name}已经存在或%s' % sqlite3.IntegrityError)

    def update_data(self):
        for date in self.update_date_list:  # 遍历更新日期列表
            df = self.get_data_from_tushare_wait(date)  # 下载数据（从数据库最后日期到今天的
            df = self.process_data(df, date)  # 处理数据
            self.write_sqlite_data(df, date)  # 写入数据库
            self.record(self.today)           # 记录更新

    def pull(self):
        # 判断现在到没到更新频率
        self.last_date = self.get_last_date()                # 更新最新记录日期
        frequency_date = self.get_frequency_date()           # 依据更新频率，设置更新日期
        self.today = datetime.datetime.today()               # 记录现在时间 2023-04-29 10:15:59.517954
        if self.today <= frequency_date:
            print(f'{self.to_table.__tablename__}已经更新到{self.last_date}, 现在不需要，大于{frequency_date}再更新')
            return
        # 判断更新日期是不是到了日历最新
        self.record_cal = self.get_record_cal()              # 数据记录日历
        self.get_end_date()                                  # 依据today，向前取日历结束日期
        if self.last_date == self.end_date:                  # 如果记录日期更新到日历结束日期，停止；否则继续
            print(f'表{self.to_table.__tablename__}已更新到最近的日期{self.end_date}')
            return
        self.update_date_list = self.get_update_date_list()  # 数据更新日期列表
        self.update_data()                                   # 更新数据


if __name__ == '__main__':
    result = DetailDataBase().get_last_day()
    print(result)


