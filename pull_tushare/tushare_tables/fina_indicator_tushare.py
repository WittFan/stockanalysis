""" 财务指标下载 fina_indicator_vip（按 ts_code 逐个下载） """
import sys
sys.path.append('.')

from config import pro
from pull_tushare.tushare_tables.financial_by_code_base import FinancialByCodeBase
from orm_models.table_models import FinaIndicator


class FinaIndicatorTushare(FinancialByCodeBase):
    TABLE     = FinaIndicator
    PK_COL    = 'ts_code_end_date'
    PK_FIELDS = ['ts_code', 'end_date']
    API       = pro.fina_indicator_vip


if __name__ == '__main__':
    FinaIndicatorTushare().pull()
