import sqlite3
import pandas as pd
from functools import partial
from models.config import sqlite3_url, SQLITE_URI
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine, delete, update, text

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

    @staticmethod
    def delete_data():
        """ 删除表或表中数据 delete_magic: delete(User).where(User.name=='梁山') """
        session.commit()  # 提交
        session.close()   # 关闭

    @staticmethod
    def delete_table(model):
        """ 删除表或表中数据 delete_magic: delete(User).where(User.name=='梁山') """
        model.__table__.drop(engine)

    def query(self, query_magic):
        """用 sqlAlchemy 的 session.query 查询数据库，结合pandas.read_sql"""
        df = pd.read_sql(query_magic.statement, query_magic.session.bind)
        session.close()
        return df

    @staticmethod
    def update(update_magic):
        # 进行更新操作
        session.execute(update_magic)
        # 提交与关闭
        session.commit()
        session.close()

    @staticmethod
    def sql(sql_str):
        data = session.execute(sql_str)
        session.close()
        df = pd.DataFrame(data)
        return df

data_api = DataApi()

if __name__ == '__main__':
    pass
    from models import data_api
    from models import *
    # 1.增加数据
    df = pd.DataFrame([['SSE', '20230415', 1, '20230414'],
                       ['SSE', '20230414', 1, '20230413']],
                      columns=['exchange', 'cal_date', 'is_open', 'pretrade_date'])
    data_api.write(df, Test.__tablename__)

    # 2.删除数据

    # 按照条件删除表数据
    # session.execute(delete(Test).filter(Test.cal_date=='20230415'))
    # data_api.delete_data()

    # # 清空表
    # session.execute(delete(Test))
    # data_api.delete_data()

    # 删除表
    # data_api.delete_table(Test)

    # # 3.更新数据
    # update_magic = update(Test).where(Test.cal_date == "20230415").values(cal_date="王老五")
    # data_api.update(update_magic)
    #
    # 4.查询数据
    # query_magic = session.query(Test).filter(Test.id > 0).filter(Test.exchange=='SSE')
    # df = data_api.query(query_magic)
    # print(df)

    # 5.原生sql
    df = data_api.sql(text('select * from test;'))
    print(df)
