from config import tushare_api
from models import *
from models.api import *
import pandas as pd
import datetime, time


class PullStockDaily:
    def __init__(self, table_model):
        self.table_model = table_model
        self.today = datetime.datetime.now()

    def get_record_cal(self):
        # 股票的交易日历
        # SSE开始于19901219 SZSE开始于19910703，因此只需要SSE。返回的交易日历仅仅是从开始时间到今年最后一天，扣除节假日。
        query_magic = session.query(TradeCal.cal_date).filter(TradeCal.is_open==1 and TradeCal.exchange==1)
        trade_cal = data_api.query(query_magic)['cal_date'][::-1]
        trade_cal = list(trade_cal)
        return trade_cal

    def get_last_day(self):
        """读取本地数据库最新日期的数据"""
        # 从数据库的update_date_record中查询更新的最后一个日期
        conn = sqlite3.connect(self.data_api.database)
        c = conn.cursor()
        self.last_day_sql=f"""select trade_date from {self.table_name} where ts_code=='update_date_record' order
                 by rowid desc limit 1;"""
        c.execute(self.last_day_sql)
        conn.commit()
        date = c.fetchall()
        if date == []:
            return None
        date = date[0][0]
        conn.close()
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

    def run(self):
        self.last_day = self.get_last_day()  # 更新的最新日期
        self.record_cal = self.get_record_cal()  # 数据记录日历
        self.get_end_date()  # 获取结束日期
        if self.last_day == self.end_date:  # 如果更新到今天，停止；否则获取更新日期列表
            print(f'表{self.table_name}已更新到最近的日期{self.end_date}')
            return
        self.update_date_list = self.get_update_date_list()  # 数据更新日期列表
        self.update_data()

if __name__ == '__main__':
    result = PullStockDaily(Daily).get_record_cal()
    print(result)


