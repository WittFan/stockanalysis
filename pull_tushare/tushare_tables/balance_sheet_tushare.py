""" 资产负债表下载 balancesheet_vip """
import sys
sys.path.append('.')

from config import pro
from pull_tushare.tushare_tables.financial_vip_base import FinancialVipBase
from orm_models.table_models import BalanceSheet


class BalanceSheetTushare(FinancialVipBase):
    def __init__(self):
        super().__init__()
        self.vip_api    = pro.balancesheet_vip
        self.to_table   = BalanceSheet
        self.fields     = None
        self.pk_cols    = ['ts_code', 'end_date', 'report_type']
        self.pk_col_name = 'ts_code_end_date_report_type'


if __name__ == '__main__':
    BalanceSheetTushare().pull()
