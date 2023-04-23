import sqlite3
import pandas as pd
from functools import partial
from models.config import sqlite3_url, SQLITE_URI
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine

engine = create_engine(SQLITE_URI, echo=False)  # 操作数据句柄
Session = sessionmaker(bind=engine)  # 这里一定要用上下文去管理session,否则会出现很多诡异的情况！！！切记
session = scoped_session(Session)  # 创建数据库链接池，直接使用session即可为当前线程拿出一个链接对象conn #内部会采用threading.local进行隔离

class DataApi:
    def __init__(self):
        self.database = sqlite3_url

    @staticmethod
    def write(dataframe, table_name):
        """
        将数据写入本地sqlite
        :param dataframe:
        :param table_name:
        :return:
        """
        dataframe.to_sql(table_name, engine, if_exists='append', index=False)

    def query(self, query_magic):
        """用 sqlAlchemy 的 session.query 查询数据库，结合pandas.read_sql"""
        df = pd.read_sql(query_magic.statement, query_magic.session.bind)
        session.close()
        return df

    @staticmethod
    def delete_table(table_name):
        """ 删除表 """
        conn = sqlite3.connect(sqlite3_url)
        c = conn.cursor()
        "创建表index_dailybasic表"
        sql = """drop table %s""" % table_name
        c.execute(sql)
        conn.commit()
        conn.close()

    @staticmethod
    def delete_data(table_name, ts_code):
        """ 删除数据 """
        conn = sqlite3.connect(sqlite3_url)
        c = conn.cursor()
        "创建表index_dailybasic表"
        sql = """delete from %s where ts_code=='%s'""" % (table_name, ts_code)
        c.execute(sql)
        conn.commit()
        conn.close()

data_api = DataApi()

if __name__ == '__main__':
    pass
    from models import data_api
    from models import *
    # 1.增加数据
    df = pd.DataFrame([['SSE', '20230415', 1, '20230414'],
                       ['SSE', '20230414', 1, '20230413']],
                      columns=['exchange', 'cal_date', 'is_open', 'pretrade_date'])
    data_api.write(df, Test.__name__)

    # 2.查询数据
    query_magic = session.query(Test).filter(Test.id > 1).filter(Test.exchange=='SSE')
    df = data_api.query(query_magic)
    print(df)

    # 3.删除表
    # DataApi.delete_table('index_daily')
    # delete_table('trade_cal')
    # 删除数据

    # from TushareApi import TushareApi
    # api = TushareApi()
    # for i in api.ts_code_set:
    #     delete_data('index_daily', i)
    # data_api = DataApi()
    # print(data_api.index_dailybasic(ts_code='000001.SH', start_date='20040108', end_date='20230322'))