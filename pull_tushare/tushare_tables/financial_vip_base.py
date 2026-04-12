""" 财务报表 VIP 接口下载基类
与 DetailDataBase 的区别：
  - DetailDataBase 按交易日历逐日下载（trade_date 维度）
  - FinancialVipBase 按季度报告期逐期下载（period/end_date 维度）
    每次调用 from_api(period=...) 获取该报告期所有股票的数据
"""
import datetime
import time

import pandas as pd
from sqlalchemy import asc, text

from config import pro
from orm_models.table_models import *
from orm_models.api import engine, session, data_api
from utils import today_todatetime
from utils.logger import LoggerTushare


def _gen_report_periods(start_year=1990):
    """生成所有 A 股季度报告期，从 start_year Q4 到今天（格式：datetime）"""
    periods = []
    today = datetime.date.today()
    year = start_year
    while True:
        for month, day in [(3, 31), (6, 30), (9, 30), (12, 31)]:
            d = datetime.datetime(year, month, day)
            if d.date() > today:
                return periods
            periods.append(d)
        year += 1


class FinancialVipBase:
    """按季度报告期下载财务报表数据的基类"""

    def __init__(self):
        self.from_api = pro.income_vip   # 子类覆盖
        self.to_table = None             # 子类覆盖，例如 IncomeStatement
        self.primary_keys = ['ts_code', 'end_date', 'report_type']  # 子类可覆盖
        self.pk_col = 'ts_code_end_date_report_type'                 # 主键列名，子类可覆盖
        self.to_datetime_list = ['ann_date', 'f_ann_date', 'end_date']
        self.logger = LoggerTushare(self.__class__.__name__).logger
        self.today = today_todatetime()

    # ────────────────────────────── 进度管理 ──────────────────────────────

    def get_downloaded_periods(self) -> set:
        """查询已下载过的报告期（从 UpdateRecord 读取）"""
        query = session.query(UpdateRecord.data_datetime).filter(
            UpdateRecord.table_name == self.to_table.__tablename__
        ).order_by(asc(UpdateRecord.data_datetime))
        df = data_api.query(query)
        if len(df) == 0:
            return set()
        # data_datetime 存储的是 datetime，直接转为 set
        return set(df['data_datetime'].tolist())

    def get_all_periods(self) -> list:
        """返回 1990Q4 至今全部季度报告期列表"""
        return _gen_report_periods()

    # ────────────────────────────── 数据获取 ──────────────────────────────

    def _fetch_period(self, period_str: str) -> pd.DataFrame:
        """调用 Tushare API 下载单个报告期数据（自动重试）"""
        while True:
            try:
                df = self.from_api(period=period_str)
                return df if df is not None else pd.DataFrame()
            except Exception as e:
                self.logger.info(
                    f'下载 {self.to_table.__tablename__} period={period_str} 遇到限流，等待10秒: {e}'
                )
                time.sleep(10)

    # ────────────────────────────── 数据处理 ──────────────────────────────

    def _convert_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """将日期字符串列转换为 datetime"""
        for col in self.to_datetime_list:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        return df

    def _set_primary_key(self, df: pd.DataFrame) -> pd.DataFrame:
        """拼接主键列（子类可覆盖）"""
        df[self.pk_col] = df[self.primary_keys[0]].astype(str)
        for key in self.primary_keys[1:]:
            df[self.pk_col] = df[self.pk_col] + df[key].astype(str)
        return df

    # ────────────────────────────── 写库 ──────────────────────────────────

    def _upsert(self, df: pd.DataFrame, period_dt: datetime.datetime):
        """将单期数据写入数据库（先删同期旧数据，再插入新数据）"""
        if df is None or len(df) == 0:
            return

        df = self._convert_dates(df)
        df = self._set_primary_key(df)

        # end_date 转 str 用于 SQL 删除（DuckDB 支持 ISO 格式）
        period_iso = period_dt.strftime('%Y-%m-%d')

        with engine.begin() as con:
            # 删除该报告期旧数据（避免重复）
            con.execute(
                text(f"DELETE FROM {self.to_table.__tablename__} WHERE end_date = '{period_iso}'")
            )
            df.to_sql(self.to_table.__tablename__, con=con, if_exists='append', index=False)

            # 写入更新记录
            record = pd.DataFrame([{
                'table_name': self.to_table.__tablename__,
                'data_datetime': period_dt,
                'created_datetime': self.today,
                'table_name_data_datetime': self.to_table.__tablename__ + str(period_dt),
            }])
            record.to_sql(UpdateRecord.__tablename__, con=con, if_exists='append', index=False)

    # ────────────────────────────── 主入口 ────────────────────────────────

    def pull(self):
        """下载所有未覆盖的季度报告期"""
        all_periods = self.get_all_periods()
        downloaded = self.get_downloaded_periods()
        pending = [p for p in all_periods if p not in downloaded]

        if not pending:
            self.logger.info(f'{self.to_table.__tablename__} 已更新到最新季度，无需下载')
            return

        self.logger.info(
            f'{self.to_table.__tablename__} 共 {len(all_periods)} 个报告期，'
            f'已下载 {len(downloaded)} 个，待下载 {len(pending)} 个'
        )

        for i, period_dt in enumerate(pending):
            period_str = period_dt.strftime('%Y%m%d')
            df = self._fetch_period(period_str)
            self._upsert(df, period_dt)

            # 每 20 期打一次进度日志
            if (i + 1) % 20 == 0 or (i + 1) == len(pending):
                pct = round((i + 1) / len(pending) * 100, 1)
                self.logger.info(
                    f'{self.to_table.__tablename__} 进度: {i + 1}/{len(pending)} ({pct}%)'
                )
