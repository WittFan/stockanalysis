"""
数据库的模型，模型使用sqlalchemy的ORM方法，面向对象的关系映射。
"""
import os
import platform

from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import scoped_session
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


"""
Sqlite连接：注意注意注意：这个URI连接的相对地址，指的是相对于最外层调用的文件的相对位置，而不是此文件的相对位置。所以最好是使用绝对路径。
"""
# 获取当前文件的绝对路径
SQLITE_URI = None
if str(platform.system().lower()) == 'windows':
    path = __file__.replace(fr"\{os.path.basename(__file__)}", "").replace("\\\\", "\\")
    SQLITE_URI = fr'sqlite:///{path}\data\fast.db''?check_same_thread=False'
    print(f'数据库路径：{SQLITE_URI}')
elif str(platform.system().lower()) == 'linux' or 'darwin':
    path = __file__.replace(fr"/{os.path.basename(__file__)}", "").replace("//", "/")
    SQLITE_URI = fr'sqlite:///{path}/data/fast.db''?check_same_thread=False'
    print(f'数据库路径：{SQLITE_URI}')
else:
    pass
    print(f"未知系统：{platform.system().lower()}")

# 定义表的基类
Base = declarative_base()

class TushareTradeCal(Base):
    __tablename__ = "tushare_trade_cal"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exchange = Column(String, index=True, comment='交易所 SSE上交所 SZSE深交所')
    cal_date = Column(String, index=True, comment='日历日期')
    is_open = Column(String, index=True, comment='是否交易 0休市 1交易')
    pretrade_date = Column(String, comment='上一个交易日')

class TushareStockBasic(Base):
    __tablename__ = "tushare_stock_basic"
    ts_code = Column(String, primary_key=True, comment='TS代码')
    symbol = Column(String, comment='股票代码')
    name = Column(String, index=True, comment='股票名称')
    area = Column(String, comment='地域')
    industry = Column(String, comment='所属行业')
    fullname = Column(String, comment='股票全称')
    enname = Column(String, comment='英文全称')
    cnspell = Column(String, comment='拼音缩写')
    market = Column(String, index=True, comment='市场类型')
    exchange = Column(String, index=True, comment='交易所代码')
    curr_type = Column(String, comment='交易货币')
    list_status = Column(String, index=True, comment='上市状态 L上市 D退市 P暂停上市')
    list_date = Column(String, comment='上市日期')
    delist_date = Column(String, comment='退市日期')
    is_hs = Column(String, index=True, comment='是否沪深港通标的，N否 H沪股通 S深股通')

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


# 操作数据句柄
engine = create_engine(SQLITE_URI)

Session = sessionmaker(bind=engine)
# 这里一定要用上下文去管理session,否则会出现很多诡异的情况！！！切记
# session = Session()
# 创建数据库链接池，直接使用session即可为当前线程拿出一个链接对象conn
# 内部会采用threading.local进行隔离
session = scoped_session(Session)
# 删除表
# Base.metadata.drop_all(engine)
# 创建表
Base.metadata.create_all(engine)


