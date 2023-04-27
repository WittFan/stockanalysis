""" 注册的sqlAlchemy ORM表主要是记录数据下载信息，验证数据完整性的信息"""

from models.base import Base  # 多个model继承同一个Base
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

class UpdateRecord(Base):
    """交易日历表"""
    __tablename__ = "update_record"
    id = Column(Integer, primary_key=True, autoincrement=True)
    table = Column(String, index=True, comment='更新的表')
    datetime = Column(DateTime, index=True, comment='表内数据时间')
    created_datetime = Column(DateTime, index=True, comment='更新时间')

class VerifyRecord(Base):
    __tablename__ = "verify_record"
    id = Column(Integer, primary_key=True, autoincrement=True)
    table = Column(String, index=True, comment='更新的表')
    completeness = Column(String, index=True, comment='是否完整 1完整 0不完整')
    created_datetime = Column(DateTime, index=True, comment='更新时间')