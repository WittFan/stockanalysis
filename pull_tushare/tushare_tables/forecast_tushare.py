""" 业绩预告下载 forecast_vip """
import sys
sys.path.append('.')

from config import pro
from pull_tushare.tushare_tables.financial_vip_base import FinancialVipBase
from orm_models.table_models import FinaForecast


class ForecastTushare(FinancialVipBase):
    def __init__(self):
        super().__init__()
        self.vip_api    = pro.forecast_vip
        self.to_table   = FinaForecast
        self.fields     = None
        self.pk_cols    = ['ts_code', 'ann_date', 'end_date']
        self.pk_col_name = 'ts_code_ann_date_end_date'


if __name__ == '__main__':
    ForecastTushare().pull()
