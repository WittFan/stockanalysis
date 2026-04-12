""" 财务指标下载 (fina_indicator_vip)
与三张报表不同：主键只有 ts_code + end_date（无 report_type），
同时 Tushare API 按 period 参数查询。
"""
import sys
sys.path.append('.')

from config import pro
from orm_models.table_models import FinaIndicator
from pull_tushare.tushare_tables.financial_vip_base import FinancialVipBase


class FinaIndicatorTushare(FinancialVipBase):
    def __init__(self):
        super().__init__()
        self.from_api = pro.fina_indicator_vip
        self.to_table = FinaIndicator
        self.primary_keys = ['ts_code', 'end_date']
        self.pk_col = 'ts_code_end_date'
        self.to_datetime_list = ['ann_date', 'end_date']


if __name__ == '__main__':
    FinaIndicatorTushare().pull()
