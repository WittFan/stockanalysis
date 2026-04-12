""" 资产负债表下载 balancesheet_vip（按 ts_code 逐个下载） """
import sys
sys.path.append('.')

from config import pro
from pull_tushare.tushare_tables.financial_by_code_base import FinancialByCodeBase
from orm_models.table_models import BalanceSheet


class BalanceSheetTushare(FinancialByCodeBase):
    TABLE     = BalanceSheet
    PK_COL    = 'ts_code_end_date_report_type'
    PK_FIELDS = ['ts_code', 'end_date', 'report_type']
    API       = pro.balancesheet_vip


if __name__ == '__main__':
    BalanceSheetTushare().pull()
