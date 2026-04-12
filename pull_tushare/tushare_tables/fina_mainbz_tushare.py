""" 主营业务构成下载 fina_mainbz_vip """
import sys
sys.path.append('.')

from config import pro
from pull_tushare.tushare_tables.financial_vip_base import FinancialVipBase
from orm_models.table_models import FinaMainbz


class FinaMainbzTushare(FinancialVipBase):
    def __init__(self):
        super().__init__()
        self.vip_api    = pro.fina_mainbz_vip
        self.to_table   = FinaMainbz
        self.fields     = None
        self.pk_cols    = ['ts_code', 'end_date', 'bz_item', 'curr_type']
        self.pk_col_name = 'ts_code_end_date_bz_item_curr_type'


if __name__ == '__main__':
    FinaMainbzTushare().pull()
