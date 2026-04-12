"""
财报披露日期下载 disclosure_date
说明：无 VIP 批量接口，但支持按 end_date 一次获取全市场数据，
      复用 FinancialVipBase，覆盖 _fetch_period 方法。
"""
import sys
sys.path.append('.')

import time
import pandas as pd
from loguru import logger as loguru_logger

from config import pro
from pull_tushare.tushare_tables.financial_vip_base import FinancialVipBase
from orm_models.table_models import DisclosureDate


class DisclosureDateTushare(FinancialVipBase):
    def __init__(self):
        super().__init__()
        self.to_table   = DisclosureDate
        self.fields     = None
        self.pk_cols    = ['ts_code', 'end_date']
        self.pk_col_name = 'ts_code_end_date'

    def _fetch_period(self, period):
        """ 覆盖：按 end_date 批量获取（无分页限制，单次最大3000条） """
        while True:
            try:
                df = pro.disclosure_date(end_date=period)
                break
            except Exception as e:
                loguru_logger.warning(f'disclosure_date period={period} 等待20秒重试: {e}')
                time.sleep(20)
        return df if df is not None else pd.DataFrame()


if __name__ == '__main__':
    DisclosureDateTushare().pull()
