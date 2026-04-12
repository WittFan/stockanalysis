"""
财务数据按 ts_code 下载基类 FinancialByCodeBase

说明：
  - 适用于 income_vip / cashflow_vip / balancesheet_vip / fina_indicator_vip
  - 全量首次下载：遍历所有 ts_code，每只标的下载全部历史报告
  - 增量下载：检查最新财报季，参照 disclosure_date 表的计划披露日期（pre_date），
    只对已到披露日期且尚无该季数据的 ts_code 下载新增数据（不删除旧数据）
  - 断点续传：全量时跳过数据表中已有数据的 ts_code（利用实际数据而非额外记录）
  - Upsert 策略（全量）：先按 ts_code DELETE 已有行，再 INSERT
  - Insert 策略（增量）：只插入新增数据，不删除旧数据
  - 写入前自动过滤 API 返回但表中不存在的多余列
"""
import datetime
import time
import pandas as pd
from loguru import logger as loguru_logger
from sqlalchemy import text

from orm_models.api import data_api, engine, session
from orm_models.table_models import StockBasic, UpdateRecord


class FinancialByCodeBase:
    TABLE     = None    # ORM 模型类（子类赋值）
    PK_COL    = ''      # 复合主键列名，如 'ts_code_end_date_report_type'
    PK_FIELDS = []      # 主键字段列表，如 ['ts_code', 'end_date', 'report_type']
    API       = None    # Tushare API 函数（如 pro.income_vip）

    def __init__(self):
        self.begin_time = datetime.datetime.now()

    # ──────────────────────────────────────────────
    # 内部工具方法
    # ──────────────────────────────────────────────

    def _make_pk(self, row):
        return '_'.join(str(row[c]) if row[c] is not None else '' for c in self.PK_FIELDS)

    def _filter_columns(self, df):
        """过滤 API 返回但目标表中不存在的多余列"""
        table_name = self.TABLE.__tablename__
        table_cols = {c.name for c in self.TABLE.__table__.columns}
        extra_cols = set(df.columns) - table_cols
        if extra_cols:
            loguru_logger.debug(f'{table_name} 丢弃 API 多余列: {extra_cols}')
            df = df[[c for c in df.columns if c in table_cols]]
        return df

    def _process_df(self, df):
        if df.empty:
            return df
        df = df.copy()
        df[self.PK_COL] = df.apply(self._make_pk, axis=1)
        # 同一主键可能有多条记录（原始报告 update_flag=0 + 修正报告 update_flag=1），
        # 按 ann_date + update_flag 排序后保留最新一条，避免 INSERT 时主键冲突
        sort_cols = []
        if 'ann_date' in df.columns:
            sort_cols.append('ann_date')
        if 'update_flag' in df.columns:
            sort_cols.append('update_flag')
        if sort_cols:
            df = df.sort_values(sort_cols, na_position='first')
        df = df.drop_duplicates(subset=self.PK_COL, keep='last')
        return df

    def _upsert_by_code(self, df, ts_code: str):
        """全量模式：按 ts_code 整体替换（删除该标的全部旧数据，再插入新数据）。"""
        if df.empty:
            return
        table_name = self.TABLE.__tablename__
        df = self._filter_columns(df)
        with engine.begin() as con:
            con.execute(text(
                f"DELETE FROM \"{table_name}\" WHERE ts_code = '{ts_code}'"
            ))
            df.to_sql(table_name, con=con, if_exists='append', index=False)

    def _insert_new_rows(self, df, ts_code: str):
        """
        增量模式：只插入数据表中不存在的新行（按主键判断），不删除旧数据。
        返回实际新增的行数。
        """
        if df.empty:
            return 0
        table_name = self.TABLE.__tablename__
        df = self._filter_columns(df)
        # 查询该 ts_code 已有的主键集合
        try:
            with engine.connect() as con:
                result = con.execute(text(
                    f"SELECT \"{self.PK_COL}\" FROM \"{table_name}\" WHERE ts_code = '{ts_code}'"
                ))
                existing_pks = {row[0] for row in result}
        except Exception:
            existing_pks = set()
        # 过滤出新行
        new_df = df[~df[self.PK_COL].isin(existing_pks)]
        if new_df.empty:
            return 0
        with engine.begin() as con:
            new_df.to_sql(table_name, con=con, if_exists='append', index=False)
        return len(new_df)

    def _get_all_ts_codes(self) -> list:
        """从 StockBasic 获取全市场 ts_code"""
        df = data_api.query(session.query(StockBasic.ts_code))
        return list(df['ts_code'])

    def _get_done_ts_codes(self) -> set:
        """从数据表 SELECT DISTINCT ts_code，用于全量断点续传"""
        table_name = self.TABLE.__tablename__
        try:
            with engine.connect() as con:
                result = con.execute(text(f'SELECT DISTINCT ts_code FROM "{table_name}"'))
                return {row[0] for row in result}
        except Exception:
            return set()

    def _get_latest_season(self) -> str:
        """返回最近已过去的季末日期字符串（YYYYMMDD）"""
        today = datetime.date.today()
        for month, day in reversed([(3, 31), (6, 30), (9, 30), (12, 31)]):
            d = datetime.date(today.year, month, day)
            if d <= today:
                return d.strftime('%Y%m%d')
        # 万一今天是 1 月 1 日，取上一年 Q4
        return datetime.date(today.year - 1, 12, 31).strftime('%Y%m%d')

    def _get_done_codes_for_season(self, season: str) -> set:
        """查询某财报季已有数据的 ts_code 集合"""
        table_name = self.TABLE.__tablename__
        try:
            with engine.connect() as con:
                result = con.execute(text(
                    f"SELECT DISTINCT ts_code FROM \"{table_name}\" WHERE end_date = '{season}'"
                ))
                return {row[0] for row in result}
        except Exception:
            return set()

    def _get_due_codes_for_season(self, season: str) -> set:
        """
        从 disclosure_date 表查询计划披露日期（pre_date）已到今天的 ts_code 集合。
        即：pre_date <= 今天，说明该公司应该已经披露了该季度财报。
        如果 disclosure_date 表中没有该季度的数据，返回空集（跳过增量）。
        """
        today_str = datetime.date.today().strftime('%Y%m%d')
        try:
            with engine.connect() as con:
                result = con.execute(text(
                    f"SELECT DISTINCT ts_code FROM disclosure_date "
                    f"WHERE end_date = '{season}' AND pre_date <= '{today_str}'"
                ))
                return {row[0] for row in result}
        except Exception:
            return set()

    def _get_last_update_flag(self) -> bool:
        """UpdateRecord 中是否存在该表的记录（判断全量是否已完成）"""
        from sqlalchemy import desc
        query_magic = session.query(UpdateRecord.data_datetime).filter(
            UpdateRecord.table_name == self.TABLE.__tablename__
        ).limit(1)
        df = data_api.query(query_magic)
        return not df.empty

    def _record(self, date_str: str):
        """写 UpdateRecord，date_str 格式 YYYYMMDD"""
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
    # 主入口方法
    # ──────────────────────────────────────────────

    def pull_initial(self):
        """
        全量首次下载：遍历所有 ts_code，每只标的下载全部历史报告。
        断点续传：跳过数据表中已有数据的 ts_code。
        开始前清除旧的 UpdateRecord（旧 FinancialVipBase 可能遗留 period-based 记录）。
        """
        table_name = self.TABLE.__tablename__

        # 清除旧 period-based UpdateRecord，避免被误判为已完成
        with engine.begin() as con:
            con.execute(text(
                f"DELETE FROM update_record WHERE table_name = '{table_name}'"
            ))

        all_codes  = self._get_all_ts_codes()
        done_codes = self._get_done_ts_codes()
        pending    = [c for c in all_codes if c not in done_codes]

        if not pending:
            loguru_logger.info(f'{table_name} 所有 ts_code 已有数据，跳过全量')
            self._record(datetime.date.today().strftime('%Y%m%d'))
            return

        total_all = len(all_codes)
        loguru_logger.info(
            f'{table_name} 全量下载开始，共 {total_all} 只，'
            f'已完成 {len(done_codes)}，待下载 {len(pending)}'
        )
        total_rows = 0

        for i, code in enumerate(pending):
            while True:
                try:
                    df = self.API(ts_code=code)
                    break
                except Exception as e:
                    loguru_logger.warning(f'{table_name} ts_code={code} 等待20秒重试: {e}')
                    time.sleep(20)

            if df is not None and not df.empty:
                df = self._process_df(df)
                self._upsert_by_code(df, code)
                total_rows += len(df)

            if (i + 1) % 500 == 0 or i == len(pending) - 1:
                elapsed = datetime.datetime.now() - self.begin_time
                cur_num = len(done_codes) + i + 1
                loguru_logger.info(
                    f'{table_name} 全量进度 {code}（{cur_num}/{total_all}），'
                    f'待下载第 {i+1}/{len(pending)} 只，'
                    f'累计 {total_rows} 行，已用时 {elapsed}'
                )

        today_str = datetime.date.today().strftime('%Y%m%d')
        self._record(today_str)
        loguru_logger.info(f'{table_name} 全量下载完成，共 {total_rows} 行')

    def pull_incremental(self):
        """
        增量更新：检查最新财报季，参照 disclosure_date 表的计划披露日期，
        只对已到披露日期（pre_date <= 今天）且尚无该季数据的 ts_code 下载。
        只插入新增数据，不删除旧数据。
        """
        table_name    = self.TABLE.__tablename__
        latest_season = self._get_latest_season()

        # 1. 查询 disclosure_date 中计划披露日期已到的 ts_code
        due_codes = self._get_due_codes_for_season(latest_season)
        if not due_codes:
            loguru_logger.info(
                f'{table_name} 财报季 {latest_season} 在 disclosure_date 中无披露计划，跳过增量'
            )
            return

        # 2. 检查哪些已到披露日期的 ts_code 还没有该季数据
        done_codes = self._get_done_codes_for_season(latest_season)
        pending    = [c for c in due_codes if c not in done_codes]

        if not pending:
            loguru_logger.info(
                f'{table_name} 财报季 {latest_season} 已到披露日期的 {len(due_codes)} 只全部已更新，'
                f'等待更多公司到达披露日期'
            )
            return

        total_due = len(due_codes)
        loguru_logger.info(
            f'{table_name} 增量更新：财报季 {latest_season}，'
            f'已到披露日期 {total_due} 只，已有数据 {len(done_codes)} 只，'
            f'待更新 {len(pending)} 只'
        )
        new_rows = 0
        skipped  = 0

        for i, code in enumerate(pending):
            while True:
                try:
                    df = self.API(ts_code=code)
                    break
                except Exception as e:
                    loguru_logger.warning(f'{table_name} 增量 ts_code={code} 等待20秒重试: {e}')
                    time.sleep(20)

            if df is not None and not df.empty:
                df = self._process_df(df)
                inserted = self._insert_new_rows(df, code)
                new_rows += inserted
                if inserted == 0:
                    skipped += 1
            else:
                skipped += 1

            if (i + 1) % 500 == 0 or i == len(pending) - 1:
                elapsed = datetime.datetime.now() - self.begin_time
                loguru_logger.info(
                    f'{table_name} 增量进度 {code}（{i+1}/{len(pending)}），'
                    f'新增 {new_rows} 行，跳过 {skipped} 只（无新数据），已用时 {elapsed}'
                )

        self._record(latest_season)
        loguru_logger.info(
            f'{table_name} 增量完成，财报季 {latest_season}，'
            f'新增 {new_rows} 行，跳过 {skipped} 只（无新数据）'
        )

    def pull(self):
        """
        自动模式：
          - UpdateRecord 无该表记录 → pull_initial（全量）
          - 否则 → pull_incremental（增量，参照披露计划按财报季补全）
        """
        if not self._get_last_update_flag():
            self.pull_initial()
        else:
            self.pull_incremental()
