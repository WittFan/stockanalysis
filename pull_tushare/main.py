from pull_tushare.tushare_tables import *
import pull_tushare
import datetime

def manual_start():
    pass
    # 1.年度日历
    year_list = [TradeCalTushare]
    # 取下日历日期最后一天，上次更新到n年12月30日
    # 是否过了n年11月31，如果过了每天尝试更新下一年
    trade_cal_tushare = TradeCalTushare()
    last_day = trade_cal_tushare.get_last_day()
    # n = last_day
    today = datetime.date.today()
    if today > datetime.datetime(year=2023, month=11, day=31):
        trade_cal_tushare.pull()

    # 2.月行情
    # 取下列表的数据日期，上次更新到n月
    # 是否过了n+1月最后一个交易日，如果过了就更新到最新n月

    # 3.周线行情
    # 取下列表的数据日期，上次更新到第n周最后一日
    # 是否过了第n+1周最后一个交易日，如果过了就更新

    # 4.日更
    # 更新到今天


if __name__=="__main__":
    manual_start()