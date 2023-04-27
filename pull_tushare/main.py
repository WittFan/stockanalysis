from pull_tushare.tushare_tables import *
import pull_tushare
import datetime

def manual_start():
    """ 手动更新所有tushare数据（非定时任务）"""
    pass
    # 1.年度日历
    tushare_api_year_list = [TradeCalTushare]
    for tushare_api_object in tushare_api_year_list:
        tushare_api_object().pull()

    # 2.月行情: 股票月行情、复权行情，指数基本信息、“成分和权重”、申万行业分类、月行情，
    month_list = []
    # 建立一个线程池，遍历month_list
    # 设置pull条件
    # 取下列表的数据日期，上次更新到n月
    # 是否过了n+1月最后一个交易日，如果过了就更新到最新n月

    # 3.周线行情
    week_list = []
    # 建立一个线程池，遍历week_list
    # 设置pull条件
    # 取下列表的数据日期，上次更新到第n周最后一日
    # 是否过了第n+1周最后一个交易日，如果过了就更新

    # 4.日更
    day_list = []
    # 更新到今天


if __name__=="__main__":
    manual_start()