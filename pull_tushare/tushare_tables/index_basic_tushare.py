import sqlite3
import datetime
import pendulum

from config import tushare_api
from models.table_models import *
from models.api import *
from utils import to_datetime
from pull_tushare.tushare_tables.meta_data_base import MetaDataBase


class IndexBasicTushare(MetaDataBase):
    def __init__(self):
        super().__init__()
        self.from_api = tushare_api.index_basic
        self.to_table = IndexBasic
        self.fields = ["ts_code", "name", "fullname", "market", "publisher", "index_type", "category",
                    "base_date", "base_point", "list_date", "weight_rule", "desc", "exp_date"]

if __name__ == "__main__":
    IndexBasicTushare().pull()
