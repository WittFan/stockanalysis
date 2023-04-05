import tushare as ts
import pandas as pd
import datetime, time
import sqlite3
from sqlalchemy import create_engine

class IndexDailybasic:
    def __init__(self):
        self
        self.ts_code_set = {'000001.SH': '上证指数', '000300.SH': '沪深300', '000905.SH': '中证500', '399001.SZ': '深证成指',
                        '399005.SZ': '中小100', '399006.SZ': '创业板指', '399016.SZ': '', '399300.SZ': '沪深300',
                        '000005.SH': '商业指数', '000006.SH': '地产指数', '000016.SH': '上证５０', '399905.SZ': '中证 500'}

    @staticmethod
    def get_data(start_date, end_date, ts_code):
        """从tushare获取数据"""
        pro = ts.pro_api()
        mid_date = start_date + datetime.timedelta(days=12*360)
        if end_date <= mid_date:
            # 如果数据在12年里，则直接取数返回结果
            df = pro.index_dailybasic(start_date=start_date.strftime('%Y%m%d'), end_date=end_date.strftime('%Y%m%d'), ts_code=ts_code)
            return df
        df = pro.index_dailybasic(start_date=start_date.strftime('%Y%m%d'), end_date=mid_date.strftime('%Y%m%d'), ts_code=ts_code)
        start_date = mid_date + datetime.timedelta(days=1)
        mid_date = start_date + datetime.timedelta(days=12*360)
        while mid_date < end_date:
        # 如果mid_date没有超过end_date，就一直获取
            df2 = pro.index_dailybasic(start_date=start_date.strftime('%Y%m%d'), end_date=mid_date.strftime('%Y%m%d'), ts_code=ts_code)
            df = df.append(df2)
        # 如果mid_date超过了end_date，用end_date
        df2 = pro.index_dailybasic(start_date=start_date.strftime('%Y%m%d'), end_date=end_date.strftime('%Y%m%d'), ts_code=ts_code)
        df = df.append(df2)
        # 按照trade_date排序
        df = df.sort_values(by='trade_date')
        # 将排序前的序号删掉
        df = df.reset_index(drop=True)
        return df

    @staticmethod
    def write_data_csv(dataframe):
        """将tushare数据写入本地csv"""
        dataframe.to_csv('./data/index_dailybasic.csv', index=False)

    @staticmethod
    def set_primary_key(dataframe):
        dataframe['ts_code_trade_date'] = dataframe.apply(lambda x: x['ts_code']+str(x['trade_date']), axis=1)
        return dataframe

    @staticmethod
    def write_data_sqlite(dataframe):
        """将tushare数据写入本地sqlite"""
        conn = sqlite3.connect('data.db')
        dataframe.to_sql('index_dailybasic', conn, if_exists= 'append', index=False)
        conn.close()

    @staticmethod
    def create_table():
        """创建表index_dailybasic表"""
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        sql = """create table if not exists index_dailybasic(
            ts_code_trade_date varchar(32) PRIMARY KEY not null,
            ts_code varchar(32) not null,
            trade_date varchar(32) not null,
            total_mv float not null,
            float_mv float not null,
            total_share float not null,
            float_share float not null,
            free_share float not null,
            turnover_rate float not null,
            turnover_rate_f float not null,
            pe float not null,
            pe_ttm float not null,
            pb float not null)"""
        # 'TS代码+交易日期' 'TS代码' '交易日期'  '当日总市值（元）'
        # '当日流通市值（元）'   '当日总股本（股）' '当日流通股本（股）' '当日自由流通股本（股）'
        # '换手率' '换手率（基于自由流通股本）' '市盈率' '市盈率TTM' '市净率'
        c.execute(sql)
        conn.commit()
        conn.close()

    def pull_all_data(self):
        # 全量数据拉取到本地，并存储
        for ts_code in self.ts_code_set:
            # 遍历IndexDailybasic的所有代码ts_code
            df = self.get_data(datetime.date(2004, 1, 1), datetime.date.today(), ts_code)
            df = self.set_primary_key(df)
            try:
                self.write_data_sqlite(df)
            except sqlite3.IntegrityError:
                print('%s已经存在' %ts_code)

    def pull_new_data():
        ### 增量数据拉取到本地，并存储
        # 读取本地数据
        date = read_last_day_data()
        if date == None:
            date = datetime.date(2004, 1, 1)
        # 获取线上数据
        if date < datetime.date.today():
            # 如果本地数据已经更新到今天，就不需要再下载更新了；如果没有，进行下面的操作。
            start_date = date + datetime.timedelta(days=1)
            end_date = datetime.date.today()
            df = get_data(start_date, end_date)
            update_date = df.iloc[-1, 1]
            update_date = update_date[0:4]+'-'+update_date[4:6]+'-'+update_date[6:8]
            df = set_primary_key(df)
            # 更新本地数据
            write_data_sqlite(df)
            print('index_dailybasic成功地从%s更新到%s' %(date, update_date))
        else:
            print('index_dailybasic已经是最新%s' %(date))

    @staticmethod
    def read_last_day_data():
        """读取本地数据库最新日期的数据"""
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        sql = """select trade_date from index_dailybasic where ts_code=='000001.SH' order
         by trade_date desc limit 1;"""
        c.execute(sql)
        conn.commit()
        date = c.fetchall()
        if date == []:
            return None
        date = date[0][0]
        conn.close()
        date = datetime.date(int(date[0:4]), int(date[4:6]),int(date[6:8]))
        return date

    @staticmethod
    def read_data(ts_code, start_date, end_date):
        """

        :return:
        """
        conn = sqlite3.connect('data.db')
        sql = """select * from index_dailybasic where ts_code=='%s' and trade_date>='%s' and trade_date<='%s';""" %(ts_code, start_date, end_date)
        df = pd.read_sql_query(sql, conn)
        return df

if __name__ == '__main__':
    ts_code, start_date, end_date = '000001.SH', '2004011', '20230325'
    inde_daily_basic = IndexDailybasic()
    # inde_daily_basic.pull_all_data()
    df = inde_daily_basic.read_data(ts_code, start_date, end_date)
