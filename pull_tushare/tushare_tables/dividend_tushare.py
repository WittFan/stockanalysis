"""
分红送股数据下载 dividend
说明：无 VIP 批量接口，按 ts_code 遍历初始下载，增量按 ann_date 区间拉取。
"""
import sys
sys.path.append('.')

import datetime
import time
import pandas as pd
from loguru import logger as loguru_logger
from sqlalchemy import text

from config import pro
from orm_models.api import data_api, engine, session
from orm_models.table_models import Dividend, StockBasic, UpdateRecord


class DividendTushare:
    TABLE = Dividend
    PK_COL = 'ts_code_end_date_div_proc'
    PK_FIELDS = ['ts_code', 'end_date', 'div_proc']

    def __init__(self):
        self.begin_time = datetime.datetime.now()

    # ──────────────────────────────────────────────

    def _make_pk(self, row):
        return '_'.join(str(row[c]) if row[c] is not None else '' for c in self.PK_FIELDS)

    def _process_df(self, df):
        if df.empty:
            return df
        df = df.copy()
        df[self.PK_COL] = df.apply(self._make_pk, axis=1)
        return df

    def _upsert(self, df):
        if df.empty:
            return
        table_name = self.TABLE.__tablename__
        pk_values = df[self.PK_COL].tolist()
        batch = 500
        with engine.begin() as con:
            for i in range(0, len(pk_values), batch):
                chunk = pk_values[i:i + batch]
                placeholders = ','.join([f"'{v}'" for v in chunk])
                con.execute(text(
                    f"DELETE FROM {table_name} WHERE {self.PK_COL} IN ({placeholders})"
                ))
            df.to_sql(table_name, con=con, if_exists='append', index=False)

    def _get_all_ts_codes(self):
        """ 从 StockBasic 获取所有股票代码 """
        df = data_api.query(session.query(StockBasic.ts_code))
        return list(df['ts_code'])

    def _get_last_ann_date(self):
        """ 从 UpdateRecord 获取最后一次增量更新的日期 """
        from sqlalchemy import desc
        query_magic = session.query(UpdateRecord.data_datetime).filter(
            UpdateRecord.table_name == self.TABLE.__tablename__
        ).order_by(desc(UpdateRecord.data_datetime)).limit(1)
        df = data_api.query(query_magic)
        if df.empty or df.iloc[0, 0] is None:
            return None
        val = df.iloc[0, 0]
        if hasattr(val, 'strftime'):
            return val.strftime('%Y%m%d')
        return str(val)[:10].replace('-', '')

    def _record(self, date_str):
        """ 写 UpdateRecord，date_str 格式 YYYYMMDD """
        table_name = self.TABLE.__tablename__
        period_dt = datetime.datetime.strptime(date_str, '%Y%m%d')
        now = datetime.datetime.now()
        pk_val = table_name + date_str
        df_record = pd.DataFrame([{
            'table_name_data_datetime': pk_val,
            'table_name': table_name,
            'data_datetime': period_dt,
            'created_datetime': now,
        }])
        with engine.begin() as con:
            con.execute(text(
                f"DELETE FROM update_record WHERE table_name_data_datetime = '{pk_val}'"
            ))
            df_record.to_sql(UpdateRecord.__tablename__, con=con, if_exists='append', index=False)

    # ──────────────────────────────────────────────

    def pull_initial(self):
        """ 全量下载：遍历所有 ts_code """
        table_name = self.TABLE.__tablename__
        ts_codes = self._get_all_ts_codes()
        loguru_logger.info(f'{table_name} 开始全量下载，共 {len(ts_codes)} 只股票')
        total_rows = 0

        for i, code in enumerate(ts_codes):
            while True:
                try:
                    df = pro.dividend(ts_code=code)
                    break
                except Exception as e:
                    loguru_logger.warning(f'{table_name} ts_code={code} 等待20秒重试: {e}')
                    time.sleep(20)
            if df is not None and not df.empty:
                df = self._process_df(df)
                self._upsert(df)
                total_rows += len(df)

            if (i + 1) % 500 == 0 or i == len(ts_codes) - 1:
                elapsed = datetime.datetime.now() - self.begin_time
                pct = round((i + 1) / len(ts_codes) * 100, 1)
                loguru_logger.info(f'{table_name} 进度 {pct}%（{i+1}/{len(ts_codes)}），累计 {total_rows} 行，已用时 {elapsed}')

        today_str = datetime.date.today().strftime('%Y%m%d')
        self._record(today_str)
        loguru_logger.info(f'{table_name} 全量下载完成，共 {total_rows} 行')

    def pull_incremental(self, days=30):
        """ 增量：按 ann_date 区间拉最近 N 天 """
        table_name = self.TABLE.__tablename__
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        loguru_logger.info(f'{table_name} 增量更新：ann_date [{start_str}, {end_str}]')
        while True:
            try:
                df = pro.dividend(start_date=start_str, end_date=end_str)
                break
            except Exception as e:
                loguru_logger.warning(f'{table_name} 增量请求等待20秒重试: {e}')
                time.sleep(20)
        if df is None or df.empty:
            loguru_logger.info(f'{table_name} 增量无新数据')
            return
        df = self._process_df(df)
        self._upsert(df)
        self._record(end_str)
        loguru_logger.info(f'{table_name} 增量写入 {len(df)} 条')

    def pull(self):
        last = self._get_last_ann_date()
        if last is None:
            self.pull_initial()
        else:
            self.pull_incremental()


if __name__ == '__main__':
    DividendTushare().pull()
