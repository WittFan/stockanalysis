"""  股票每日指标  """
import sys
sys.path.append('.')

from pull_tushare.tushare_tables.detail_data_base import *


class DailyBasicTushare(DetailDataBase):
    def __init__(self):
        super().__init__()
        self.from_api = pro.daily_basic
        self.to_table = DailyBasic
        self.fields = None
        self.to_datetime_list = ['trade_date']
        self.frequency = 'daily'

    def get_data_from_tushare(self, date):
        df = self.from_api(trade_date=date.strftime('%Y%m%d'), fields=self.fields, flag=1)
        return df

if __name__ == '__main__':
    DailyBasicTushare().pull()