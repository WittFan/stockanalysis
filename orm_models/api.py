from config import DB_URI
from sqlalchemy import select, create_engine, text, delete, desc, asc
from sqlalchemy.orm import sessionmaker, scoped_session, load_only
import pandas as pd
from functools import partial
import pendulum
from datetime import datetime
from orm_models import table_models
from orm_models.table_models import TradeCal  # 运行时仅用到 TradeCal

engine  = create_engine(DB_URI, echo=False)
Session = sessionmaker(bind=engine)
session = scoped_session(Session)


def init_db():
    """
    创建所有 ORM 表（如不存在）。
    应在 Flask/脚本启动时显式调用，而非在导入时自动执行。
    """
    import orm_models.table_models  # noqa: F401 — 触发所有 Model 类注册到 metadata
    from orm_models.base import Base
    from loguru import logger
    Base.metadata.create_all(engine)
    logger.info("数据库初始化完成（表已就绪）")


class DataApi:
    def __init__(self):
        pass

    @staticmethod
    def write(dataframe, table_model):
        """
        将数据写入本地sqlite
        :param dataframe:
        :param table_name:
        :return:
        """
        dataframe.to_sql(table_model.__tablename__, engine, if_exists='append', index=False)

    @staticmethod
    def delete_data(delete_magic):
        """ 删除表或表中数据 delete_magic: delete(User).where(User.name=='梁山') """
        session.execute(delete_magic)
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

    def read(self, table_name, **kwargs):
        """
        当前存在点问题kwargs不能使用多个
        """
        # 构造 SQL 查询语句
        # 输出的字段fields
        table_model = getattr(table_models, table_name)
        try:
            fields = kwargs['fields']
            model_fields = []
            for i in fields:
                model_fields.append(getattr(table_model, i))
            query_magic = session.query(*model_fields)
        except:
            query_magic = session.query(table_model)
        # 查询的字段
        for key, value in kwargs.items():
            if key == 'fields':  # 因为前面对fields进行了处理
                continue
            elif key == 'start_date':
                query_magic = getattr(query_magic, 'filter')
                query_magic = query_magic(getattr(table_model, 'trade_date') >= value)
            elif key == 'end_date':
                query_magic = getattr(query_magic, 'filter')
                query_magic = query_magic(getattr(table_model, 'trade_date') <= value)
            else:
                query_magic = getattr(query_magic, 'filter')
                query_magic = query_magic(getattr(table_model, key) == value)
        df = self.query(query_magic)
        return df

    def read_symbols(self, table_model, symbols, fields, start_datetime=datetime(1990,12,1), end_datetime=datetime.now()):
        """
        table_name: 数据库中的表名
        symbols: 股票等标的代码['000001.SH', '0000003.SH']
        start_datetime: 开始时间
        end_datetime: 结束时间
        fields: 输出字段
        """
        # 表名-->表模型，查询表
        # table_model = getattr(table_models, table_name)
        stmt = select(table_model)

        # 如果标的代码非空，增加symbol条件。否则查询全部标的代码
        if symbols:
            # 等价于 stmt.where(table_model.ts_code.in_(symbols))
            stmt = getattr(stmt, 'where')(table_model.ts_code.in_(symbols))

        # 开始时间 默认是1990年1月1日
        stmt = getattr(stmt, 'filter')(table_model.trade_date >= start_datetime)
        # 结束时间 默认是现在
        stmt = getattr(stmt, 'filter')(table_model.trade_date <= end_datetime)

        # 将fields字段转换为表模型的字段，table_model.field
        field_object_list =[]
        if fields:
            for column_name in fields:
                field_object_list.append(getattr(table_model, column_name))
        # 选择table_name，时间在（start_datetime, end_datetime）之间，股票代码在symbols列表里，按照时间正序排序，只加载fields里的列
            stmt = getattr(stmt, 'options')(load_only(*field_object_list))
        stmt = getattr(stmt, 'order_by')(asc(table_model.trade_date))
        df = pd.read_sql(stmt, session.bind)
        session.close()
        return df

    def basic_info(self):
        df1 = self.read('StockBasic')
        df2 = self.read('IndexBasic')
        df3 = self.read('FundBasic')
        df = pd.concat([df1, df2, df3], axis=0)
        return df

    def get_SSE_cal(self):
        # 股票的交易日历
        # SSE开始于19901219 SZSE开始于19910703，因此只需要SSE。返回的交易日历仅仅是从开始时间到今年最后一天，扣除节假日。
        query_magic = session.query(TradeCal).filter(TradeCal.exchange=='SSE').filter(TradeCal.is_open == '1').order_by(asc(TradeCal.cal_date))
        trade_cal = pd.DataFrame(self.query(query_magic)['cal_date'])
        return trade_cal

    def __getattr__(self, table_name):
        """
        DataApi.name ， name为表名
        使用：
        data_api = DataApi()
        data_api.index_dailybasic('000001.SH', '20040101', '20230101')
        :param name:
        :return:
        """
        return partial(self.read, table_name)

# 创建实体
data_api = DataApi()

if __name__ == '__main__':
    pass
    from orm_models.table_models import *
    # 1.增加数据
    # data_list = [['SSE', pendulum.parse('20230415'), 1, pendulum.parse('20230414')],
    #              ['SSE', pendulum.parse('20230414'), 1, pendulum.parse('20230413')]]
    # df = pd.DataFrame(data_list, columns=['exchange', 'cal_date', 'is_open', 'pretrade_date'])
    # data_api.write(df, Test)

    # 2.删除数据
    # 按照条件删除表数据
    # delete_magic = delete(UpdateRecord).filter(UpdateRecord.table_name=='fund_nav')
    # data_api.delete_data(delete_magic)
    # # 清空表
    # delete_magic = session.execute(delete(Test))
    # data_api.delete_data()

    # 删除表
    # data_api.delete_table(IndexMember)

    # # 3.更新数据
    # update_magic = update(Test).where(Test.cal_date == "20230415").values(cal_date="王老五")
    # data_api.update(update_magic)
    #
    # 4.查询数据
    # query_magic = session.query(Test.id, Test.cal_date).filter(Test.exchange=='SSE')
    # df = data_api.query(query_magic)
    # query_magic = session.query(TradeCal)
    # df = data_api.query(query_magic)
    # print(df)

    # # 5.原生sql
    # df = data_api.sql(text('select * from test;'))
    # print(df)

    # ## 6.dot表名查询
    # from datetime import datetime
    # start_time = datetime.now()
    # df = data_api.Daily(fields=['cal_date'], start_date=datetime(2023,9,1))
    # time_spend = datetime.now() - start_time
    # print(df)
    # print(df.columns)
    # print(time_spend)

    # 根据symbol获取数据
    # from datetime import datetime
    # df = data_api.read_symbols(Daily, symbols=[], fields=[],start_datetime=datetime(2023, 9, 1), end_datetime=datetime(2023, 9, 28))
    # print(df)
    # print(df.columns)

    # # 7.获取日历
    # print(data_api.get_SSE_cal())

    #
    df = data_api.basic_info()
    df.to_excel('basic_info.xlsx')
    print(df)
