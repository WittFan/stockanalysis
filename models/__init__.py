"""
   SqlAichemy ORM数据模型
"""
# models.py 模块下各个文件的用处

# table models模块
# 将各个文件下（exchange_info.py 等）的table model导入__init__.py，导入models模块后可以直接使用这些table model
# base.py # 基类
from .exchange_info import *
from .foreign_currency import *
from .index import *
from .reports import *
from .stock_info import *
from .stock_trade import *
from .update_info import *


# 处理数据库的模块
# from .api import *           # 数据接口，有类DataApi
# models_usage_example.py    models使用实验
# register.py                注册数据模型