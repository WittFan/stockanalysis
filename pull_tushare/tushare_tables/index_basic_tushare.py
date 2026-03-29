""" 指数基本信息 """
from config import pro
from orm_models.api import *
from pull_tushare.tushare_tables.meta_data_base import MetaDataBase
from orm_models.table_models import *

class IndexBasicTushare(MetaDataBase):
    def __init__(self):
        super().__init__()
        self.from_api = pro.index_basic
        self.to_table = IndexBasic
        self.fields = ["ts_code", "name", "fullname", "market", "publisher", "index_type", "category",
                    "base_date", "base_point", "list_date", "weight_rule", "desc", "exp_date"]
        self.frequency = 'monthly'

    def down(self):
        """ 下载数据 """
        # MSCI指数 中证指数 上交所指数 深交所指数 中金指数 申万指数 其他指数
        market_code_list = ['MSCI', 'CSI', 'SSE', 'SZSE', 'CICC', 'SW', 'OTH']
        df = pd.DataFrame()
        for market_code in market_code_list:
            df1 = self.from_api(market=market_code, fields=self.fields)
            df = pd.concat([df1, df], axis=0)
        if len(df) == 0:
            self.logger.error(f'{self.to_table.__tablename__}下载失败')
        return df

if __name__ == "__main__":
    IndexBasicTushare().pull()
    # print(data_api.get_SSE_cal())
