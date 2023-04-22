""" 配置数据模型及数据库的属性 """
import os
import platform

# 获取当前文件的绝对路径，改成数据库路径
SQLITE_URI = None
if str(platform.system().lower()) == 'windows':
    path = os.path.dirname(__file__).replace('models', 'data')
    SQLITE_URI = fr'sqlite:///{path}\fast.db''?check_same_thread=False'
    sqlite3_url = path + '\fast.db'
    # print(f'数据库路径：{SQLITE_URI}')
elif str(platform.system().lower()) == 'linux' or 'darwin':
    path = os.path.dirname(__file__).replace('models', 'data')
    SQLITE_URI = fr'sqlite:///{path}/fast.db''?check_same_thread=False'
    sqlite3_url = path + '/fast.db'
    # print(f'数据库路径：{SQLITE_URI}')
else:
    pass
    # print(f"未知系统：{platform.system().lower()}")

