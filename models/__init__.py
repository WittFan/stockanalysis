"""
   SqlAichemy ORM数据模型
"""
# 将各个文件下（exchange_catagory.py 等）的table model导入__init__.py，导入models模块后可以直接使用这些table model
from .exchange_catagory import *
from .foreign_currency import *
from .index import *
from .reports import *
from .stock_info import *
from .stock_trade import *
from .update_info import *

# 注册文件 register.py
