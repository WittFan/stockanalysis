""" 现金流量表下载 (cashflow_vip) """
import sys
sys.path.append('.')

from config import pro
from orm_models.table_models import CashFlow
from pull_tushare.tushare_tables.financial_vip_base import FinancialVipBase


class CashFlowTushare(FinancialVipBase):
    def __init__(self):
        super().__init__()
        self.from_api = pro.cashflow_vip
        self.to_table = CashFlow
        self.primary_keys = ['ts_code', 'end_date', 'report_type']
        self.pk_col = 'ts_code_end_date_report_type'
        self.to_datetime_list = ['ann_date', 'f_ann_date', 'end_date']


if __name__ == '__main__':
    CashFlowTushare().pull()
