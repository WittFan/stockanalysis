""" 注册的sqlAlchemy ORM表主要是股票交易信息"""
from .base import Base
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    Float,
    String,
    Enum,
    DECIMAL,
    DateTime,
    Boolean,
    UniqueConstraint,
    Index
)

class Daily(Base):
    __tablename__ = "daily"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, index=True, comment='股票代码')
    trade_date = Column(String, index=True, comment='交易日期')
    open = Column(Float, comment='开盘价')
    high = Column(Float, comment='最高价')
    low = Column(Float, comment='最低价')
    close = Column(Float, comment='收盘价')
    pre_close = Column(Float, comment='昨收价')
    change = Column(Float, comment='涨跌额')
    pct_chg = Column(Float, comment='涨跌幅')
    vol = Column(Float, comment='成交量')
    amount = Column(Float, comment='成交额')

class Weekly(Base):
    __tablename__ = "weekly"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, index=True, comment='')
    trade_date = Column(String, index=True, comment='')
    close = Column(Float, comment='')
    open = Column(Float, comment='')
    high = Column(Float, comment='')
    low = Column(Float, comment='')
    pre_close = Column(Float, comment='')
    change = Column(Float, comment='')
    pct_chg = Column(Float, comment='')
    vol = Column(Float, comment='')
    amount = Column(Float, comment='')

class Monthly(Base):
    __tablename__ = "monthly"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, index=True, comment='')
    trade_date = Column(String, index=True, comment='')
    close = Column(Float, comment='')
    open = Column(Float, comment='')
    high = Column(Float, comment='')
    low = Column(Float, comment='')
    pre_close = Column(Float, comment='')
    change = Column(Float, comment='')
    pct_chg = Column(Float, comment='')
    vol = Column(Float, comment='')
    amount = Column(Float, comment='')

class AdjFactor(Base):
    __tablename__ = "adj_factor"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, index=True, comment='股票代码')
    trade_date = Column(String, index=True, comment='交易日期')
    adj_factor = Column(Float, comment='复权因子')

class DailyBasic(Base):
    __tablename__ = "daily_basic"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, index=True, comment='TS股票代码')
    trade_date = Column(String, index=True, comment='交易日期')
    close = Column(Float, comment='当日收盘价')
    turnover_rate = Column(Float, comment='换手率')
    turnover_rate_f = Column(Float, comment='换手率(自由流通股)')
    volume_ratio = Column(Float, comment='量比')
    pe = Column(Float, comment='市盈率（总市值/净利润）')
    pe_ttm = Column(Float, comment='市盈率（TTM）')
    pb = Column(Float, comment='市净率（总市值/净资产）')
    ps = Column(Float, comment='市销率')
    ps_ttm = Column(Float, comment='市销率（TTM）')
    dv_ratio = Column(Float, comment='股息率（%）')
    dv_ttm = Column(Float, comment='股息率（TTM） （%）')
    total_share = Column(Float, comment='总股本')
    float_share = Column(Float, comment='流通股本')
    free_share = Column(Float, comment='自由流通股本')
    total_mv = Column(Float, comment='总市值')
    circ_mv = Column(Float, comment='流通市值')
    limit_status = Column(Integer, comment='涨跌停状态')

class StockMx(Base):
    __tablename__ = "stock_mx"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, index=True, comment='TS股票代码')
    trade_date = Column(String, index=True, comment='交易日期')
    close = Column(Float, comment='当日收盘价')
    turnover_rate = Column(Float, comment='换手率')
    turnover_rate_f = Column(Float, comment='换手率(自由流通股)')
    volume_ratio = Column(Float, comment='量比')
    pe = Column(Float, comment='市盈率（总市值/净利润）')
    pe_ttm = Column(Float, comment='市盈率（TTM）')
    pb = Column(Float, comment='市净率（总市值/净资产）')
    ps = Column(Float, comment='市销率')
    ps_ttm = Column(Float, comment='市销率（TTM）')
    dv_ratio = Column(Float, comment='股息率（%）')
    dv_ttm = Column(Float, comment='股息率（TTM） （%）')
    total_share = Column(Float, comment='总股本')
    float_share = Column(Float, comment='流通股本')
    free_share = Column(Float, comment='自由流通股本')
    total_mv = Column(Float, comment='总市值')
    circ_mv = Column(Float, comment='流通市值')

    # 20.动能因子stock_mx
"""create table if not exists (
             ts_code_trade_date varchar(32) PRIMARY KEY not null,
             ts_code varchar(32) not null,
             trade_date varchar(32) not null,
             mx_grade int(1),
             com_stock varchar(32),
             evd_v varchar(32),
             zt_sum_z varchar(32),
             wma250_z varchar(32));"""

    # 21.估值因子stock_vx
"""create table if not exists stock_vx(
             ts_code_trade_date varchar(32) PRIMARY KEY not null,
             ts_code varchar(32) not null,
             trade_date varchar(32) not null,
             level1 varchar(32),
             level2 varchar(32),
             vx_life_v_l4 varchar(32),
             vx_3excellent_v_l4 varchar(32),
             vx_past_5q_avg_l4 varchar(32),
             vx_grow_worse_v_l4 varchar(32),
             vx_life_v_l8 varchar(32),
             vx_3excellent_v_l8 varchar(32),
             vx_past_5q_avg_l8 varchar(32),
             vx_grow_worse_v_l8 varchar(32),
             vxx varchar(32),
             vs varchar(32),
             vz11 varchar(32),
             vz24 varchar(32),
             vz_lms varchar(32));"""