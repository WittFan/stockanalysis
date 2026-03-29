"""  公募基金净值  """
import sys
sys.path.append('.')

from pull_tushare.tushare_tables.detail_data_base import *


class FundNavTushare(DetailDataBase):
    def __init__(self):
        super().__init__()
        self.from_api = pro.fund_nav
        self.to_table = FundNav
        self.fields = ["ts_code", "ann_date", "nav_date", "unit_nav", "accum_nav", "accum_div", "net_asset", "total_netasset", "adj_nav", "update_flag"]
        self.to_datetime_list = ["ann_date", "nav_date"]
        self.frequency = 'daily'
        self.limit = None
        self.update_flag = 1

    def get_record_cal(self):
        # 返回的自然日历
        # SSE开始于19901219 SZSE开始于19910703，因此只需要SSE。基金开始于1999.1.8，仅仅是从开始时间到今年最后一天。
        query_magic = session.query(TradeCal).filter(TradeCal.exchange=='SSE').filter(TradeCal.cal_date>=datetime.datetime(1999,1,8)).order_by(asc(TradeCal.cal_date))
        trade_cal = data_api.query(query_magic)['cal_date']
        trade_cal = list(trade_cal)
        return trade_cal

    def get_data_from_tushare(self, date, **kwargs):
        df = self.from_api(nav_date=date.strftime('%Y%m%d'), fields=self.fields)
        return df

    def set_primary_key(self, df):
        # 添加primary key
        df['ts_code_nav_date'] = df.apply(lambda x: x['ts_code'] + str(x['nav_date']), axis=1)
        return df

if __name__ == '__main__':
    ind_obj = FundNavTushare()
    judge = 0

    # 测试get_data_from_tushare_unlimit方法，得到的是update_flag=1的数据
    if judge == 0:
        df = ind_obj.get_data_from_tushare_unlimit(datetime.datetime(2021, 9, 30))
        print(df, len(df))

    if judge == 1:
        ind_obj.pull()

    if judge == 2:
        df = ind_obj.get_data_from_tushare_unlimit(datetime.datetime(2021, 9, 30))
        df = ind_obj.process_data(df)
        print(df, len(df))
        df.to_csv('fund_nav.csv')