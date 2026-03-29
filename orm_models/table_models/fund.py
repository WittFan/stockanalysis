""" 注册的sqlAlchemy ORM表主要是指数相关"""
from orm_models.base import Base # 多个model继承同一个Base
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

class FundBasic(Base):
    __tablename__ = "fund_basic"
    ts_code = Column(String, primary_key=True, comment='基金代码')
    name = Column(String, index=True, comment='简称')
    management = Column(String, comment='管理人')
    custodian = Column(String, comment='托管人')
    fund_type = Column(String, comment='投资类型')
    found_date = Column(DateTime, comment='成立日期')
    due_date = Column(DateTime, comment='到期日期')
    list_date = Column(DateTime, comment='上市时间')
    issue_date = Column(DateTime, comment='发行日期')
    delist_date = Column(DateTime, comment='退市日期')
    issue_amount = Column(Float, comment='发行份额(亿份)')
    m_fee = Column(Float, comment='管理费')
    c_fee = Column(Float, comment='托管费')
    duration_year = Column(Float, comment='存续期')
    p_value = Column(Float, comment='面值')
    min_amount = Column(Float, comment='起点金额(万元)')
    exp_return = Column(Float, comment='预期收益率')
    benchmark = Column(String, comment='业绩比较基准')
    status = Column(String, index=True, comment='存续状态D摘牌 I发行 L已上市')
    invest_type = Column(String, comment='投资风格')
    type = Column(String, comment='基金类型')
    trustee = Column(String, comment='受托人')
    purc_startdate = Column(DateTime, comment='日常申购起始日')
    redm_startdate = Column(DateTime, comment='日常赎回起始日')
    market = Column(String, index=True, comment='E场内O场外')

class FundNav(Base):
    """ 公募基金净值
        单位净值：每份基金的净值。
        累计净值：单位净值 + 历史分红
        复权单位净值：单位净值 + 历史分红 + 分红再投入的收益
        取update_flag最大的一条
    """
    __tablename__ = "fund_nav"
    ts_code_nav_date = Column(String, primary_key=True)
    ts_code = Column(String, index=True, comment='TS代码')
    ann_date = Column(DateTime, comment='公告日期')
    nav_date = Column(DateTime, index=True, comment='截止日期')
    unit_nav = Column(Float, comment='单位净值')
    accum_nav = Column(Float, comment='累计净值')
    accum_div = Column(Float, comment='累计分红')
    net_asset = Column(Float, comment='资产净值')
    total_netasset = Column(Float, comment='合计资产净值')
    adj_nav = Column(Float, comment='复权单位净值')
    update_flag = Column(String, comment='更新标识')

class FundDaily(Base):
    """
    获取场内基金日线行情，类似股票日行情
    单次最大2000行记录，总量不限制
    """
    __tablename__ = "fund_daily"
    ts_code_trade_date = Column(String, primary_key=True)
    ts_code = Column(String, index=True, comment='TS代码')
    trade_date = Column(DateTime, index=True, comment='交易日期')
    pre_close = Column(Float, comment='昨收盘价(元)')
    open = Column(Float, comment='开盘价(元)')
    high = Column(Float, comment='最高价(元)')
    low = Column(Float, comment='最低价(元)')
    close = Column(Float, comment='收盘价(元)')
    change = Column(Float, comment='涨跌(元)')
    pct_chg = Column(Float, comment='涨跌幅(%)')
    vol = Column(Float, comment='成交量(手)')
    amount = Column(Float, comment='成交金额(千元)')

class FundAdj(Base):
    """
    获取基金复权因子，用于计算基金复权行情
    单次最大提取2000行记录，可循环提取，数据总量不限制
    """
    __tablename__ = "fund_adj"
    ts_code_trade_date = Column(String, primary_key=True)
    ts_code = Column(String, index=True, comment='股票代码')
    trade_date = Column(DateTime, index=True, comment='交易日期')
    adj_factor = Column(Float, comment='复权因子')