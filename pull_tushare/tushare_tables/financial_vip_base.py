"""
财务数据下载基类 FinancialVipBase
说明：
  - 适用于 Tushare 5000积分 VIP 财务接口（income_vip / balancesheet_vip 等）
  - 支持按季末 period 批量拉取全市场数据（效率远高于逐只股票遍历）
  - 两种模式：
      pull_initial()     → 全量历史（遍历所有未完成的季末 period）
      pull_incremental() → 增量（按最近 N 天的 ann_date 拉新公告）
  - UpdateRecord 按 (table_name, period) 维度记录，已完成的 period 跳过
  - Upsert 策略：先按主键 DELETE 当前批次已有行，再 INSERT，支持 update_flag 数据修正
"""
import datetime
import time
import pandas as pd
from loguru import logger as loguru_logger
from sqlalchemy import text, delete

from config import pro
from orm_models.api import data_api, engine, session
from orm_models.table_models import UpdateRecord


class FinancialVipBase:
    def __init__(self):
        self.vip_api    = None          # Tushare VIP API 函数，如 pro.income_vip
        self.to_table   = None          # SQLAlchemy ORM 模型类
        self.fields     = None          # 下载字段列表（None = 全部字段）
        self.pk_cols    = []            # 主键字段名列表，如 ['ts_code','end_date','report_type']
        self.pk_col_name = ''           # ORM 模型中的主键列名，如 'ts_code_end_date_report_type'
        self.start_year = 2000          # 历史数据起始年份
        self.begin_time = datetime.datetime.now()

    # ──────────────────────────────────────────────
    # 内部工具方法
    # ──────────────────────────────────────────────

    def _gen_period_list(self):
        """ 生成从 start_year 至当前季度的所有季末日期字符串，格式 YYYYMMDD """
        periods = []
        today = datetime.date.today()
        year = self.start_year
        while year <= today.year:
            for month, day in [(3, 31), (6, 30), (9, 30), (12, 31)]:
                d = datetime.date(year, month, day)
                if d > today:
                    break
                periods.append(d.strftime('%Y%m%d'))
            year += 1
        return periods

    def _get_done_periods(self):
        """ 从 UpdateRecord 查询已完成的 period 集合（table_name + period 为主键） """
        table_name = self.to_table.__tablename__
        query_magic = session.query(UpdateRecord.data_datetime).filter(
            UpdateRecord.table_name == table_name
        )
        df = data_api.query(query_magic)
        if df.empty:
            return set()
        # data_datetime 存储的是 period 字符串对应的 datetime，还原为 YYYYMMDD 字符串
        done = set()
        for val in df['data_datetime']:
            if val is not None:
                if hasattr(val, 'strftime'):
                    done.add(val.strftime('%Y%m%d'))
                else:
                    done.add(str(val)[:10].replace('-', ''))
        return done

    def _fetch_period(self, period):
        """
        调用 VIP API 按 period 拉取全市场数据，自动处理分页（Tushare 单次上限 5000 行）。
        子类可覆盖此方法以支持不同的 API 调用方式（如 disclosure_date）。
        """
        offset, dfs = 0, []
        limit = 5000
        while True:
            try:
                if self.fields:
                    df = self.vip_api(period=period, fields=','.join(self.fields),
                                      limit=limit, offset=offset)
                else:
                    df = self.vip_api(period=period, limit=limit, offset=offset)
            except Exception as e:
                loguru_logger.warning(f'{self.to_table.__tablename__} period={period} 等待20秒重试: {e}')
                time.sleep(20)
                continue
            if df is None or df.empty:
                break
            dfs.append(df)
            if len(df) < limit:
                break
            offset += limit
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    def _make_pk(self, row):
        """ 根据 pk_cols 生成复合主键字符串 """
        return '_'.join(str(row[c]) if row[c] is not None else '' for c in self.pk_cols)

    def _process_df(self, df):
        """ 生成复合主键列，丢弃空行 """
        if df.empty:
            return df
        df = df.copy()
        df[self.pk_col_name] = df.apply(self._make_pk, axis=1)
        return df

    def _upsert(self, df):
        """
        按主键 upsert：DELETE 已存在的行，再 INSERT 新数据。
        支持 update_flag 数据修正场景。
        写入前自动过滤 API 返回但表中不存在的多余列。
        """
        if df.empty:
            return
        table_name = self.to_table.__tablename__
        # 过滤列：只保留目标表中存在的列，丢弃 API 多余字段
        table_cols = {c.name for c in self.to_table.__table__.columns}
        extra_cols = set(df.columns) - table_cols
        if extra_cols:
            loguru_logger.debug(f'{table_name} 丢弃 API 多余列: {extra_cols}')
            df = df[[c for c in df.columns if c in table_cols]]
        pk_values = df[self.pk_col_name].tolist()
        # 分批删除（避免 IN 子句过大）
        batch = 500
        with engine.begin() as con:
            for i in range(0, len(pk_values), batch):
                chunk = pk_values[i:i + batch]
                placeholders = ','.join([f"'{v}'" for v in chunk])
                con.execute(text(
                    f"DELETE FROM {table_name} WHERE {self.pk_col_name} IN ({placeholders})"
                ))
            df.to_sql(table_name, con=con, if_exists='append', index=False)

    def _record_period(self, period):
        """ 将 period 写入 UpdateRecord，标记该季度已完成 """
        table_name = self.to_table.__tablename__
        period_dt = datetime.datetime.strptime(period, '%Y%m%d')
        now = datetime.datetime.now()
        pk_val = table_name + period
        df_record = pd.DataFrame([{
            'table_name_data_datetime': pk_val,
            'table_name': table_name,
            'data_datetime': period_dt,
            'created_datetime': now,
        }])
        with engine.begin() as con:
            # 若已存在则覆盖
            con.execute(text(
                f"DELETE FROM update_record WHERE table_name_data_datetime = '{pk_val}'"
            ))
            df_record.to_sql(UpdateRecord.__tablename__, con=con, if_exists='append', index=False)

    # ──────────────────────────────────────────────
    # 主入口方法
    # ──────────────────────────────────────────────

    def pull_initial(self):
        """ 全量历史下载：遍历所有未完成的 period """
        table_name = self.to_table.__tablename__
        all_periods = self._gen_period_list()
        done_periods = self._get_done_periods()
        pending = [p for p in all_periods if p not in done_periods]

        if not pending:
            loguru_logger.info(f'{table_name} 所有历史 period 已下载，无需全量更新')
            return

        loguru_logger.info(f'{table_name} 开始全量下载，共 {len(pending)} 个 period（已完成 {len(done_periods)}）')
        for i, period in enumerate(pending):
            df = self._fetch_period(period)
            if df.empty:
                loguru_logger.info(f'{table_name} period={period} 无数据，跳过')
                self._record_period(period)
                continue
            df = self._process_df(df)
            self._upsert(df)
            self._record_period(period)
            if (i + 1) % 10 == 0 or i == len(pending) - 1:
                elapsed = datetime.datetime.now() - self.begin_time
                pct = round((i + 1) / len(pending) * 100, 1)
                loguru_logger.info(f'{table_name} 全量进度 {pct}%（{i+1}/{len(pending)}），已用时 {elapsed}')

        loguru_logger.info(f'{table_name} 全量下载完成，共写入 {len(pending)} 个 period')

    def pull_incremental(self, days=30):
        """
        增量更新：拉取最近 N 天内公告（按 ann_date 区间）的数据。
        注意：若全量尚未完成（UpdateRecord 为空），此方法会自动退出并提示。
        """
        table_name = self.to_table.__tablename__
        done_periods = self._get_done_periods()
        if not done_periods:
            loguru_logger.info(f'{table_name} 尚未完成全量下载，请先运行 pull_initial()')
            return

        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')

        loguru_logger.info(f'{table_name} 增量更新：ann_date [{start_str}, {end_str}]')
        try:
            if self.fields:
                df = self.vip_api(start_date=start_str, end_date=end_str,
                                  fields=','.join(self.fields))
            else:
                df = self.vip_api(start_date=start_str, end_date=end_str)
        except Exception as e:
            loguru_logger.error(f'{table_name} 增量下载失败: {e}')
            return

        if df is None or df.empty:
            loguru_logger.info(f'{table_name} 增量无新数据')
            return

        df = self._process_df(df)
        self._upsert(df)
        loguru_logger.info(f'{table_name} 增量写入 {len(df)} 条')

        # 更新 UpdateRecord 为今天
        self._record_period(end_str)

    def pull(self):
        """
        自动模式：
          - 若还有未完成的历史 period → pull_initial（全量/续传）
          - 若所有历史 period 已完成 → pull_incremental（增量）
        """
        all_periods = self._gen_period_list()
        done_periods = self._get_done_periods()
        pending = [p for p in all_periods if p not in done_periods]

        if pending:
            # 全量未完成（首次或中断续传），继续下载剩余 period
            self.pull_initial()
        else:
            self.pull_incremental()
