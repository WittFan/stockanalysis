""" 现金流量表下载 cashflow_vip（按 ts_code 逐个下载） """
import sys
sys.path.append('.')

from config import pro
from pull_tushare.tushare_tables.financial_by_code_base import FinancialByCodeBase
from orm_models.table_models import CashFlow


class CashFlowTushare(FinancialByCodeBase):
    TABLE     = CashFlow
    PK_COL    = 'ts_code_end_date_report_type'
    PK_FIELDS = ['ts_code', 'end_date', 'report_type']
    API       = pro.cashflow_vip


if __name__ == '__main__':
    CashFlowTushare().pull()
