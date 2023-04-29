"""  基础数据下载到本地的基类  """
import sqlite3
import datetime

from config import tushare_api
from models.table_models import *
from models.api import *
from utils import to_datetime


# 3.重写trade_cal

class MetaDataBase:
    def __init__(self):
        self.from_api = tushare_api.index_basic
        self.to_table = IndexBasic
        self.fields = ["ts_code", "name", "fullname", "market", "publisher", "index_type", "category",
                    "base_date", "base_point", "list_date", "weight_rule", "desc", "exp_date"]
        self.to_datetime_list = ['list_date', 'exp_date']
        self.frequency = 'monthly'

    def down(self):
        """ 下载数据 """
        df_table = self.from_api(fields=self.fields)
        if len(df_table)==0:
            print(f'{self.to_table.__tablename__}下载失败')
        return df_table

    def process(self, df_table, to_datetime_list):
        """  处理数据  """
        for column_name in to_datetime_list:
            df_table[column_name] = df_table.apply(lambda x: to_datetime(x[column_name]), axis=1)
        return df_table

    def write(self, df_table):
        """  写入数据 """
        # 删除index_basic
        data_api.delete_table(self.to_table)
        print(f'删除{self.to_table.__tablename__}')
        try:
            data_api.write(df_table, self.to_table)
            print(f'{self.to_table.__tablename__}写入成功')
        except sqlite3.IntegrityError:
            print(f'{self.to_table.__tablename__}已经存在或{sqlite3.IntegrityError}')

    def record(self, today):
        df_table = pd.DataFrame([[today]], columns=['data_datetime'])
        df_table['table'] = self.to_table.__tablename__
        df_table['created_datetime'] = today
        data_api.write(df_table, UpdateRecord)

    def pull(self):
        # 取下更细记录上数据标记日期，上次更新到n月2m日。
        query_magic = session.query(UpdateRecord.data_datetime).filter(UpdateRecord.table==self.to_table.__tablename__).limit(1)
        df_table = data_api.query(query_magic)
        # 记录现在时间 2023-04-29 10:15:59.517954
        today = datetime.datetime.today()
        if len(df_table) == 0:
            date = datetime.datetime(year=1990, month=1, day=1)
        else:
            date = df_table['data_datetime'][0]
        # 是否过了n+1月25，如果过了每天尝试更新n+1月
        dates = {'yearly': datetime.datetime(year=date.year, month=11, day=25),
                 'monthly': datetime.datetime(year=date.year, month=date.month+1, day=25),}
        if today > dates[self.frequency]:
            df_table = self.down()       # 下载数据
            df_table = self.process(df_table, self.to_datetime_list)  # 处理数据
            self.write(df_table)         # 写入数据
            self.record(today)     # 记录更新
        else:
            print(f'{self.to_table.__tablename__}已经更新到{date}, 不需要再更新')


if __name__ == "__main__":
    MetaDataBase().pull()
