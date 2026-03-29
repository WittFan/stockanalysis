"""  股票日线行情  """
import sys
sys.path.append('.')

from pull_tushare.tushare_tables.detail_data_base import *


class FundDailyTushare(DetailDataBase):
    def __init__(self):
        super().__init__()
        self.from_api = pro.fund_daily
        self.to_table = FundDaily
        self.fields = None
        self.to_datetime_list = ['trade_date']
        self.frequency = 'daily'
        self.limit = 2000

    def get_record_cal(self):
        # 返回的自然日历
        # SSE开始于19901219 SZSE开始于19910703，因此只需要SSE。基金开始于1999.1.8，仅仅是从开始时间到今年最后一天。
        query_magic = session.query(TradeCal).filter(TradeCal.exchange=='SSE').filter(TradeCal.cal_date>=datetime.datetime(1999,1,8)).order_by(asc(TradeCal.cal_date))
        trade_cal = data_api.query(query_magic)['cal_date']
        trade_cal = list(trade_cal)
        return trade_cal

if __name__ == '__main__':
    FundDailyTushare().pull()
    # df = FundDailyTushare().get_data_from_tushare_unlimit(datetime.datetime(2021, 11, 3))
    # print(df)