import sqlite3
import pandas as pd
from functools import partial

def write(dataframe, table_name):
    """
    将数据写入本地sqlite
    :param dataframe:
    :param table_name:
    :return:
    """
    conn = sqlite3.connect('data.db')
    dataframe.to_sql(table_name, conn, if_exists='append', index=False)
    conn.close()

def delete_table(table_name):
    """创建表"""
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    "创建表index_dailybasic表"
    sql = """drop table %s""" %table_name
    c.execute(sql)
    conn.commit()
    conn.close()

def delete_data(table_name, ts_code):
    """创建表"""
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    "创建表index_dailybasic表"
    sql = """delete from %s where ts_code=='%s'""" %(table_name, ts_code)
    c.execute(sql)
    conn.commit()
    conn.close()

def read(table_name, ts_code, start_date, end_date):
    """
    从sqlite数据库读index_dailybasic数据
    :return:
    df = pro.index_dailybasic(trade_date='20181018', fields='ts_code,trade_date,turnover_rate,pe')
    """
    conn = sqlite3.connect('data.db')
    sql = """select * from %s where ts_code=='%s' and trade_date>='%s' and trade_date<='%s';""" %(table_name, ts_code, start_date, end_date)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def query(table_name, **kwargs):
    # 构造 SQL 查询语句
    # 输出的字段
    try:
        fields = kwargs['fields']
        sql_field =''
        for i in fields:
            sql_field += f'{i},'
        sql_field = sql_field[:-1]
        query = f"SELECT {sql_field} FROM {table_name} WHERE "
    except:
        query = f"SELECT * FROM {table_name} WHERE"
    # 查询的字段
    for key, value in kwargs.items():
        if key == 'fields': # 因为前面对fields进行了处理
            continue
        elif key == 'start_date':
            query += f"trade_date >= '{value}' AND "
        elif key == 'end_date':
            query += f"trade_date <= '{value}' AND "
        else:
            query += f"{key} == '{value}' AND "
    query = query[:-5]+';'  # 去掉最后一个的' AND '
    conn = sqlite3.connect('data.db')  # 连接数据库
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


class DataApi:
    def __init__(self):
        pass

    def __getattr__(self, table_name):
        """
        DataApi.name ， name为表名
        使用：
        data_api = DataApi()
        data_api.index_dailybasic('000001.SH', '20040101', '20230101')
        :param name:
        :return:
        """
        return partial(query, table_name)

if __name__ == '__main__':
    pass
    # delete_table('trade_cal')
    # 删除数据

    # from TushareApi import TushareApi
    # api = TushareApi()
    # for i in api.ts_code_set:
    #     delete_data('index_daily', i)
    # data_api = DataApi()
    # print(data_api.index_dailybasic(ts_code='000001.SH', start_date='20040108', end_date='20230322'))