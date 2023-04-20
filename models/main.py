"""
数据库的模型，模型使用sqlalchemy的ORM方法，面向对象的关系映射。
"""
import os
import platform

from sqlalchemy import MetaData
from sqlalchemy.orm import relationship, backref, sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
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
from base import Base
import models

"""
Sqlite连接：注意注意注意：这个URI连接的相对地址，指的是相对于最外层调用的文件的相对位置，而不是此文件的相对位置。所以最好是使用绝对路径。
"""
# 获取当前文件的绝对路径
SQLITE_URI = None
if str(platform.system().lower()) == 'windows':
    path = __file__.replace(fr"\{os.path.basename(__file__)}", "").replace("\\\\", "\\").replace('models', 'data')
    SQLITE_URI = fr'sqlite:///{path}\fast.db''?check_same_thread=False'
    print(f'数据库路径：{SQLITE_URI}')
elif str(platform.system().lower()) == 'linux' or 'darwin':
    path = __file__.replace(fr"\{os.path.basename(__file__)}", "").replace("//", "/").replace('models', 'data')
    SQLITE_URI = fr'sqlite:///{path}/fast.db''?check_same_thread=False'
    print(f'数据库路径：{SQLITE_URI}')
else:
    pass
    print(f"未知系统：{platform.system().lower()}")

# 操作数据句柄
engine = create_engine(SQLITE_URI, echo=True)
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


