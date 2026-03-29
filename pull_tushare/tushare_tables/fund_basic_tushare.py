""" 股票基本信息 """
import sqlite3
import datetime
import pendulum

from config import pro
from orm_models.table_models import *
from orm_models.api import *
from utils import to_datetime
from pull_tushare.tushare_tables.meta_data_base import MetaDataBase

class FundBasicTushare(MetaDataBase):
    def __init__(self):
        super().__init__()
        self.from_api = pro.fund_basic
        self.to_table = FundBasic
        self.fields = ["ts_code", "name", "management", "custodian", "fund_type", "found_date",
                       "due_date", "list_date", "issue_date", "delist_date", "issue_amount", "m_fee",
                       "c_fee", "duration_year", "p_value", "min_amount", "exp_return", "benchmark",
                       "status", "invest_type", "type", "trustee", "purc_startdate", "redm_startdate", "market"]
        self.to_datetime_list = ['found_date', 'due_date', 'list_date', 'issue_date', 'delist_date', 'purc_startdate', 'redm_startdate']
        self.frequency = 'monthly'
        self.limit = 15000


if __name__ == "__main__":
    FundBasicTushare().pull()
