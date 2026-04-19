"""股票池管理表"""
from orm_models.base import Base
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime


class StockPool(Base):
    """用户自定义股票池（由 stockpool.xlsx 导入或前端增删改查）"""
    __tablename__ = "stock_pool"
    id        = Column(Integer, primary_key=True, autoincrement=True, comment='自增ID')
    ts_code   = Column(String, nullable=False, unique=True, index=True, comment='TS代码，如 600519.SH')
    name      = Column(String, nullable=False, comment='标的名称')
    in_date   = Column(String, nullable=True, comment='入池日期 YYYY-MM-DD')
    out_date  = Column(String, nullable=True, comment='出池日期 YYYY-MM-DD')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
