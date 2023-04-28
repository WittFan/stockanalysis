import sqlite3
import datetime
import pendulum

from config import tushare_api
from models.table_models import *
from models.api import *


class IndexBasicTushare:
    def __init__(self):
        self.from_api = tushare_api.trade_cal
        self.to_table = IndexBasic

    def down_write(self):
        """ 下载数据，写入数据 """
        df =tushare_api.index_basic(
            fields=["ts_code", "name", "fullname", "market", "publisher", "index_type", "category",
                    "base_date", "base_point", "list_date", "weight_rule", "desc", "exp_date"])
        # 处理数据
        def to_datetime(x):
            try:
                x = pendulum.parse(x)
            except:
                x = None
            return x
        df['list_date'] = df.apply(lambda x: to_datetime(x['list_date']), axis=1)
        df['exp_date'] = df.apply(lambda x: to_datetime(x['exp_date']), axis=1)
        # 删除index_basic
        data_api.delete_table(IndexBasic)
        print('删除index_basic')
        print(df)
        try:
            data_api.write(df, IndexBasic)
            print('index_basic下载成功')
        except sqlite3.IntegrityError:
            print('index_basic已经存在或%s' % sqlite3.IntegrityError)

    def record(self, today):
        df = pd.DataFrame([[today]], columns=['data_datetime'])
        df['table'] = 'index_basic'
        df['created_datetime'] = today
        print(df)
        data_api.write(df, UpdateRecord)

    def pull(self):
        # 取下日历日期最后一天，上次更新到n月30日
        query_magic = session.query(UpdateRecord.data_datetime).filter(UpdateRecord.table=='index_basic').limit(1)
        df = data_api.query(query_magic)
        print(df)
        today = datetime.datetime.today()
        if len(df)==0:
            self.down_write()
            self.record(today)
            return
        else:
            date = df['data_datetime'][0]
        # 是否过了n+1月25，如果过了每天尝试更新下n+1月
        if today > datetime.datetime(year=date.year, month=date.month+1, day=25):
            self.down_write()
            self.record(today)
        else:
            print(f'{self.to_table.__tablename__}已经更新到{date}, 不需要再更新')


if __name__ == "__main__":
    IndexBasicTushare().pull()
