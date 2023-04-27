from pull_tushare.tushare_tables import *
import pull_tushare
import datetime

def manual_start():
    """ 手动更新所有tushare数据（非定时任务）"""
    pass
    # 1.更新频率：年
    # 年度日历
    tushare_api_yearly_update = [TradeCalTushare]
    for tushare_api_object in tushare_api_yearly_update:
        tushare_api_object().pull()

    # 2.更新频率：月
    # 月行情: 股票月行情、复权行情，指数基本信息、“成分和权重”、申万行业分类、月行情，
    month_list = []
    # 建立一个线程池，遍历month_list
    # 设置pull条件
    # 取下列表的数据日期，上次更新到n月
    # 是否过了n+1月最后一个交易日，如果过了就更新到最新n月

    # 3.更新频率：周
    # 周线行情
    week_list = []
    # 建立一个线程池，遍历week_list
    # 设置pull条件
    # 取下列表的数据日期，上次更新到第n周最后一日
    # 是否过了第n+1周最后一个交易日，如果过了就更新

    # 4.更新频率：日
    day_list = []
    # 更新到今天


if __name__=="__main__":
    # 下一步工作：
    # 1.多线程任务，修改与数据库交互的接口，
    # 2.加上更新条件判断，加上日志
    # 3.使用说明，包括在数据库注册表，写下载数据的类，加入更新判断条件
    # 上面完成，数据部分就结束了
    manual_start()