from pull_tushare.tushare_tables import *
import pull_tushare
import datetime

def manual_start():
    """ 手动更新所有tushare数据（非定时任务）"""
    pass
    ###### 一、基础信息更新
    print(' 1.更新频率：年')
    tushare_api_yearly_basics = [TradeCalTushare] # 年度日历
    for tushare_api_object in tushare_api_yearly_basics:
        tushare_api_object().pull()

    print(' 2.更新频率：月')
    tushare_api_monthly_basics = [IndexBasicTushare, StockBasicTushare]
    # 指数基本信息、“成分和权重”、申万行业分类
    for tushare_api_object in tushare_api_monthly_basics:
        tushare_api_object().pull()
        # 设置pull条件：1、取下列表的数据日期，上次更新到n月。2、是否过了n+1月最后一个交易日，如果过了就更新到最新n月

    # 3.更新频率：周
    # 周线行情
    week_list = []
    # 建立一个线程池，遍历week_list
    # 设置pull条件：1、取下列表的数据日期，上次更新到第n周最后一日。2、是否过了第n+1周最后一个交易日，如果过了就更新

    ###### 二、明细数据更新：要建线程池
    # 4.更新频率：月
    # 股票月复权行情、月线行情，指数月线行情

    # 5.更新频率：周

    # 6.更新频率：日
    day_list = []
    # 更新到今天


if __name__=="__main__":
    # 下一步工作：
    # 任务：
    # 2.解决index_basic_tushare一次下载8000的限制

    # 1.tushare明细数据下载使用多线程任务
    # 2.加上更新条件判断，加上日志
    # 3.使用说明，包括在数据库注册表，写下载数据的类，加入更新判断条件
    # 上面完成，数据部分就结束了
    manual_start()