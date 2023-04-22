"""
   SqlAichemy ORM数据模型
"""
# models.py 模块下各个文件的用处

# table models模块
# 将各个文件下（exchange_info.py 等）的table model导入__init__.py，导入models模块后可以直接使用这些table model
from .exchange_info import *
from .foreign_currency import *
from .index import *
from .reports import *
from .stock_info import *
from .stock_trade import *
from .update_info import *
# base.py # 基类

# 处理数据库的模块
from .sqlite_data import *           # 数据接口，有类DataApi
from .config import SQLITE_URI       # 配置文件：数据库地址
# register.py                注册数据模型
# models_usage_example.py    models使用实验
