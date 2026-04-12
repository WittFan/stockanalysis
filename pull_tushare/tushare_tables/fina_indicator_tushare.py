""" 财务指标数据下载 fina_indicator_vip """
import sys
sys.path.append('.')

from config import pro
from pull_tushare.tushare_tables.financial_vip_base import FinancialVipBase
from orm_models.table_models import FinaIndicator


class FinaIndicatorTushare(FinancialVipBase):
    def __init__(self):
        super().__init__()
        self.vip_api    = pro.fina_indicator_vip
        self.to_table   = FinaIndicator
        self.fields     = None
        self.pk_cols    = ['ts_code', 'end_date']
        self.pk_col_name = 'ts_code_end_date'


if __name__ == '__main__':
    FinaIndicatorTushare().pull()
