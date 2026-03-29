"""
增量下载tushare指数日线行情
     说明：指数日线行情相对于股票日线行情，主要的难点在于有限制，必须有指数代码参数录入，这样的话就只能一个指数一个指数的下载，未到期的指数大概有8000个，这样的话每次下载指数要做8000个循环，加上分钟500次的频率限制，每天增量下载指数日行情要用16分钟。为了提升效率，全量下载没有逐日遍历，而是用的start_date、end_date两个参数，接口参数组合（ts_code,start_date, end_date），全量下载节省很多时间。
     tushare指数日线行情数据好像是3600个，index_basic里的代码在日线里没有。
     代码层面：get_data_from_tushare_unlimit()函数解除了最大行数限制，在update_data()函数里进行的逐个指数遍历。
"""
import sys
sys.path.append('.')

from pull_tushare.tushare_tables.detail_data_base import *
from orm_models.table_models import *


class IndexDailyTushare(DetailDataBase):
    def __init__(self):
        super().__init__()
        self.from_api = pro.index_daily
        self.to_table = IndexDaily
        self.fields = ["ts_code", "trade_date", "close", "open", "high", "low", "pre_close", "change", "pct_chg", "vol", "amount"]
        self.to_datetime_list = ['trade_date']
        self.frequency = 'daily'
        self.limit = 8000

    def get_record_cal(self):
        # 因为有外国数据，所以为自然日历
        # SSE开始于19901219 SZSE开始于19910703，因此按照SSE的日期，国外指数也是按照这个了。返回的交易日历仅仅是从开始时间到今年最后一天。
        query_magic = session.query(TradeCal).filter(TradeCal.exchange=='SSE').order_by(asc(TradeCal.cal_date))
        trade_cal = data_api.query(query_magic)['cal_date']
        trade_cal = list(trade_cal)
        return trade_cal

    def get_index_update_date(self, index_code):
        query_magic = session.query(IndexDaily.trade_date).filter(IndexDaily.ts_code==index_code).order_by(desc(IndexDaily.trade_date)).limit(1)
        date = data_api.query(query_magic)
        if len(date):
            date = date.iloc[0, 0]
        else:
            date = self.update_date_list[0]
        return date

    def get_data_from_tushare(self, ts_code, start_date, end_date, limit, offset):
        try:
            df = self.from_api(ts_code=ts_code, start_date=start_date.strftime('%Y%m%d'), end_date=end_date.strftime('%Y%m%d'), limit = limit, offset=offset, fields=self.fields)
        except Exception as e:
            raise e
        return df

    def get_data_from_tushare_wait(self, ts_code, start_date, end_date, limit, offset):
        # 如果接口有限制则等待10秒，直到可以继续调用
        while True:
            try:
                df = self.get_data_from_tushare(ts_code, start_date, end_date, limit, offset)
                break
            except Exception as e:
                self.logger.info(f'在下载表{self.to_table.__tablename__}指数代码{ts_code}时等待20秒')
                time.sleep(20)
        return df

    def get_data_from_tushare_unlimit(self, index_code, start_date, end_date):
        df = pd.DataFrame()
        loop_num = 0 # 循环次数
        data_length = self.limit # 为了取第一次数，data_length默认设置为limit
        # 如果返回的数据长度大于等于limit，继续遍历
        while data_length >= self.limit:
            df2 = self.get_data_from_tushare_wait(ts_code=index_code,
                start_date=start_date, end_date=end_date, limit=self.limit, offset=loop_num*self.limit) #  取数
            data_length = len(df2) # 数据长度
            df = pd.concat([df, df2], axis=0) # 合并df
            loop_num += 1 # 将循环次数加1
        df = df.sort_values(by='trade_date')
        # 将排序前的序号删掉
        df = df.reset_index(drop=True)
        return df

    def download_index_code(self):
        from config import path
        df = pd.read_excel(f'{path}/data/tushare_index_basic_info.xls')
        df = df[df['download'] == 1]  # 筛选download标记为1的
        index_code_list = list(df['ts_code'])  # 指数代码列表
        return index_code_list

    def all_index_code(self):
        df = data_api.IndexBasic(fields=['ts_code', 'exp_date'])  # 获取指数列表
        df = df[df['exp_date'].isnull()]  # 筛选截止日期还未到的
        index_code_list = list(df['ts_code']) # 指数代码列表
        return index_code_list

    def update_data(self):
        # 从本地数据库获取未到期的指数代码列表
        index_code_list = self.download_index_code()
        # 遍历指数代码，分别下载数据
        record_update_max_date = []  # 记录指数更新的最近日期
        for index_code in index_code_list:
            percent = round((index_code_list.index(index_code) + 1) / len(index_code_list) * 100, 2)
            old_percent = 0
            if  percent - old_percent >= 5:
                during_time = datetime.datetime.now() - self.begin_time
                self.logger.info(f'{self.to_table.__tablename__}写入{percent}% index_code:{index_code}，已经用时{during_time}')
                old_percent = percent
            # 将开始时间设置为index_code更新日期后的一个自然日
            update_date = self.get_index_update_date(index_code)
            end_date = self.update_date_list[-1]
            # 如果更新日期已经是end_date，则停止更新
            if update_date == end_date:
                continue
            start_date_index = self.record_cal.index(update_date)+1 # 开始日期的序号
            start_date = self.record_cal[start_date_index] # 开始日期
            df = self.get_data_from_tushare_unlimit(index_code, start_date, end_date) # 从tushare获取数据
            if len(df) == 0:
                continue
            df = self.process_data(df)  # 处理数据
            with engine.begin() as con:
                df.to_sql(self.to_table.__tablename__, con=con, if_exists='append', index=False)  # 写入数据库
            record_update_max_date.append(df['trade_date'].max())

        # 当所有index_code都完成下载后，标记更新日期到update_record上
        with engine.begin() as con:
            if record_update_max_date:
                record_data_datetime = max(record_update_max_date)
                df_record = pd.DataFrame([record_data_datetime], columns=['data_datetime'])
                df_record['table_name'] = self.to_table.__tablename__
                df_record['created_datetime'] = self.today
                df_record['table_name_data_datetime'] = df_record.apply(
                    lambda x: x['table_name'] + str(x['data_datetime']), axis=1)
                df_record.to_sql(UpdateRecord.__tablename__, con=con, if_exists='append', index=False)  # 记录更新
                # 数据更新完毕，打印日志
                during_time = datetime.datetime.now() - self.begin_time
                self.logger.info(f'{self.to_table.__tablename__}更新完毕，已经用时{during_time}')
            else:
                self.logger.info(f'{self.to_table.__tablename__}无新增数据，已经用时{during_time}')


if __name__ == '__main__':
    ind_obj = IndexDailyTushare()
    judge = 1

    # 测试get_data_from_tushare_unlimit方法
    if judge==0:
        df = ind_obj.get_data_from_tushare_unlimit(index_code='000007.SH', start_date=datetime.datetime(1992, 1, 1), end_date=datetime.datetime(2023, 10, 27))
        print(df, len(df))

    if judge==1:
        ind_obj.pull()

    if judge==2:
        index_code = '931395.CSI'
        up_date = ind_obj.get_index_update_date(index_code)
        print(up_date)
        df = data_api.read(table_name='IndexDaily', ts_code=index_code)
        print(df)
        import os
        path = os.path.dirname(__file__)
        df.to_csv(f'{path}/index_daily.csv')

    if judge==3:
        ind_obj.last_date = ind_obj.get_last_date()                # 更新最新记录日期
        frequency_date = ind_obj.get_frequency_date()           # 依据更新频率，设置更新日期边界
        ind_obj.today = today_todatetime()                      # 记录现在时间 2023-04-29 10:15:59.517954
        ind_obj.record_cal = ind_obj.get_record_cal()  # 数据记录日历
        ind_obj.end_date = ind_obj.get_end_date()  # 依据today，向前取日历结束日期
        ind_obj.update_date_list = ind_obj.get_update_date_list()  # 数据更新日期列表
        ind_obj.update_data()


