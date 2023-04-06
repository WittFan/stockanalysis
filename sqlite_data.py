import sqlite3
import pandas as pd
from functools import partial

def create_table():
    """创建表"""
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    # 1.创建股票列表stock_basic
    sql = """create table if not exists stock_basic(
            ts_code varchar(32) PRIMARY KEY not null,
            symbol varchar(32) not null,
            name varchar(32) not null,
            area varchar(32) not null,
            industry varchar(32) not null,
            fullname varchar(32) not null,
            enname varchar(32) not null,
            cnspell varchar(32) not null,
            market varchar(32) not null,
            exchange varchar(32) not null,
            curr_type varchar(32) not null,
            list_status varchar(32) not null,
            list_date varchar(32) not null,
            delist_date varchar(32) not null,
            is_hs varchar(32) not null;"""
    c.execute(sql)
    # 2.创建交易日历trade_cal
    sql = """create table if not exists trade_cal(
            exchange_cal_date varchar(32) PRIMARY KEY not null,
            exchange varchar(32) not null,
            cal_date varchar(32) not null,
            is_open varchar(32) not null,
            pretrade_date varchar(32) not null;"""
    c.execute(sql)
    # 3.创建股票曾用名namechange
    sql = """create table if not exists namechange(
                ts_code_ann_date varchar(32) PRIMARY KEY not null,
                name varchar(32) not null,
                start_date varchar(32) not null,
                end_date varchar(32) not null,
                ann_date varchar(32) not null,
                change_reason varchar(32) not null;"""
    c.execute(sql)
    # 4.创建沪深股通成份股hs_const
    sql = """create table if not exists hs_const(
                    ts_code_in_date_out_date varchar(32) PRIMARY KEY not null,
                    ts_code varchar(32) not null,
                    hs_type varchar(32) not null,
                    in_date varchar(32) not null,
                    out_date varchar(32) not null,
                    is_new varchar(32) not null;"""
    c.execute(sql)
    # 5.上市公司基本信息stock_company
    sql = """create table if not exists stock_company(
            ts_code varchar(32) PRIMARY KEY not null,
            exchange varchar(32) not null,
            chairman varchar(32) not null,
            manager varchar(32) not null,
            secretary varchar(32) not null,
            reg_capital float not null,
            setup_date varchar(32) not null,
            province varchar(32) not null,
            city varchar(32) not null,
            introduction varchar(32) not null,
            website varchar(32) not null,
            email varchar(32) not null,
            office varchar(32) not null,
            employees float not null,
            main_business varchar(32) not null,
            business_scope varchar(32) not null);"""
    c.execute(sql)
    # 6.管理层薪酬和持股stk_rewards
    sql = """create table if not exists stk_rewards(
                ts_code_name_title_ann_date varchar(32) PRIMARY KEY not null,
                ts_code varchar(32) not null,
                ann_date varchar(32) not null,
                end_date varchar(32) not null,
                name varchar(32) not null,
                title varchar(32) not null,
                reward float not null,
                hold_vol float not null;"""
    c.execute(sql)
    # 7.股东增减持stk_holdertrade
    sql = """create table if not exists stk_holdertrade(
            ts_code_ann_date_holder_name varchar(32) PRIMARY KEY not null,
            ts_code varchar(32) not null,
            ann_date varchar(32) not null,
            holder_name varchar(32) not null,
            holder_type varchar(32) not null,
            in_de varchar(32) not null,
            change_vol float not null,
            change_ratio float not null,
            after_share float not null,
            after_ratio float not null,
            avg_price float not null,
            total_share float not null,
            begin_date varchar(32) not null),
            close_date varchar(32) not null);"""
    # 创建表index_dailybasic表
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
        pb float not null);"""
    # 'TS代码+交易日期' 'TS代码' '交易日期'  '当日总市值（元）'
    # '当日流通市值（元）'   '当日总股本（股）' '当日流通股本（股）' '当日自由流通股本（股）'
    # '换手率' '换手率（基于自由流通股本）' '市盈率' '市盈率TTM' '市净率'
    c.execute(sql)
    sql = """create table if not exists index_daily(
        ts_code_trade_date varchar(32) PRIMARY KEY not null,
        ts_code varchar(32) not null,
        trade_date varchar(32) not null,
        close float not null,
        open float not null,
        high float not null,
        low float not null,
        pre_close float not null,
        change float not null,
        pct_chg float not null,
        vol float not null,
        amount float not null);"""
    # 名称	类型	描述
    # ts_code	str	TS指数代码
    # trade_date	str	交易日
    # close	float	收盘点位
    # open	float	开盘点位
    # high	float	最高点位
    # low	float	最低点位
    # pre_close	float	昨日收盘点
    # change	float	涨跌点
    # pct_chg	float	涨跌幅（%）
    # vol	float	成交量（手）
    # amount	float	成交额（千元）
    c.execute(sql)
    conn.commit()
    conn.close()

def write(dataframe, table_name):
    """
    将数据写入本地sqlite
    :param dataframe:
    :param table_name:
    :return:
    """
    conn = sqlite3.connect('data.db')
    dataframe.to_sql(table_name, conn, if_exists= 'append', index=False)
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
    """
    conn = sqlite3.connect('data.db')
    sql = """select * from %s where ts_code=='%s' and trade_date>='%s' and trade_date<='%s';""" %(table_name, ts_code, start_date, end_date)
    df = pd.read_sql_query(sql, conn)
    return df

class DataApi:
    def __init__(self):
        pass

    def __getattr__(self, name):
        """
        DataApi.name ， name为表名
        使用：
        data_api = DataApi()
        data_api.index_dailybasic('000001.SH', '20040101', '20230101')
        :param name:
        :return:
        """
        return partial(read, name)

if __name__ == '__main__':
    # create_table()

    ### 删除数据
    # from TushareApi import TushareApi
    # api = TushareApi()
    # for i in api.ts_code_set:
    #     delete_data('index_daily', i)
    data_api = DataApi()
    print(data_api.index_dailybasic('000001.SH', '20040101', '20230101'))