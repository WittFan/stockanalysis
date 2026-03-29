"""  股票日线行情  """
import sys
sys.path.append('.')

from pull_tushare.tushare_tables.detail_data_base import *


class DailyTushare(DetailDataBase):
    def __init__(self):
        super().__init__()
        self.from_api = pro.daily
        self.to_table = Daily
        self.fields = None
        self.to_datetime_list = ['trade_date']
        self.frequency = 'daily'

if __name__ == '__main__':
    DailyTushare().pull()