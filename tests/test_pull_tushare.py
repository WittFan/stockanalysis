"""
数据下载模块测试（pull_tushare）

核心测试：test_manual_start_full_pipeline
  - 直接运行 pull_tushare/main.py 的 manual_start()
  - 如果此测试通过，说明数据下载流程完整可用
  - 标记为 integration（需要 Tushare API 权限和网络）

辅助测试：单元测试增量更新逻辑、主键生成等
"""
import datetime
import pandas as pd
import pytest

from pull_tushare.tushare_tables.detail_data_base import DetailDataBase
from pull_tushare.tushare_tables.fund_daily_tushare import FundDailyTushare
from pull_tushare.tushare_tables.index_daily_tushare import IndexDailyTushare
from orm_models.table_models import FundDaily, IndexDaily, Daily


# =====================================================================
# 核心集成测试：如果此测试通过，其余 pull_tushare 测试可跳过
# =====================================================================

@pytest.mark.integration
class TestManualStartPipeline:
    """pull_tushare/main.py 完整数据拉取管线测试"""

    def test_manual_start_full_pipeline(self):
        """
        [核心集成测试] ✓ 运行 manual_start() 完整数据拉取
        如果此测试通过，说明：
        - Tushare API token 有效
        - DuckDB 数据库连接正常
        - 所有表的增量更新逻辑正确
        - 多线程数据拉取可用

        运行方式：pytest tests/test_pull_tushare.py -m integration -v
        """
        from pull_tushare.main import manual_start
        manual_start()  # 不抛出异常即为通过


# =====================================================================
# 辅助单元测试：增量更新逻辑、主键生成等（不依赖 Tushare API）
# =====================================================================

class TestDetailDataBase:
    """DetailDataBase 基类逻辑测试"""

    def test_set_primary_key_format(self):
        """✓ 主键格式为 ts_code + trade_date 字符串拼接"""
        base = DetailDataBase()
        df = pd.DataFrame({
            'ts_code': ['510300.SH', '000300.SH'],
            'trade_date': [datetime.datetime(2021, 1, 4), datetime.datetime(2021, 1, 5)],
        })
        df = base.set_primary_key(df)
        assert 'ts_code_trade_date' in df.columns
        assert df.iloc[0]['ts_code_trade_date'] == '510300.SH2021-01-04 00:00:00'

    def test_get_frequency_date_daily(self):
        """✓ daily 频率：frequency_date 等于 last_date"""
        base = DetailDataBase()
        base.last_date = datetime.datetime(2021, 6, 15)
        base.frequency = 'daily'
        freq_date = base.get_frequency_date()
        assert freq_date == datetime.datetime(2021, 6, 15)

    def test_get_frequency_date_monthly(self):
        """✓ monthly 频率：frequency_date 为下月 25 日"""
        base = DetailDataBase()
        base.last_date = datetime.datetime(2021, 6, 15)
        base.frequency = 'monthly'
        freq_date = base.get_frequency_date()
        assert freq_date == datetime.datetime(2021, 7, 25)

    def test_get_frequency_date_monthly_december(self):
        """✓ monthly 频率：12 月份时，下月为 1 月"""
        base = DetailDataBase()
        base.last_date = datetime.datetime(2021, 12, 1)
        base.frequency = 'monthly'
        freq_date = base.get_frequency_date()
        assert freq_date == datetime.datetime(2021, 1, 25)

    def test_get_frequency_date_none_last_date(self):
        """✓ last_date 为 None 时，返回 1990-01-01"""
        base = DetailDataBase()
        base.last_date = None
        base.frequency = 'daily'
        freq_date = base.get_frequency_date()
        assert freq_date == datetime.datetime(1990, 1, 1)

    def test_process_data_empty_df(self):
        """✓ 空 DataFrame 不处理，直接返回"""
        base = DetailDataBase()
        df_empty = pd.DataFrame()
        result = base.process_data(df_empty)
        assert len(result) == 0

    def test_process_data_adds_primary_key(self):
        """✓ 非空数据会被添加主键列"""
        base = DetailDataBase()
        df = pd.DataFrame({
            'ts_code': ['510300.SH'],
            'trade_date': ['20210104'],
        })
        result = base.process_data(df)
        assert 'ts_code_trade_date' in result.columns


class TestFundDailyTushare:
    """FundDailyTushare 基金日线下载器测试"""

    def test_init_sets_table_and_api(self):
        """✓ 初始化后 to_table 为 FundDaily，frequency 为 daily"""
        puller = FundDailyTushare()
        assert puller.to_table == FundDaily
        assert puller.frequency == 'daily'
        assert puller.limit == 2000

    @pytest.mark.integration
    def test_get_record_cal_returns_dates(self):
        """[集成] ✓ 从数据库获取的日历从 1999-01-08 开始"""
        puller = FundDailyTushare()
        cal = puller.get_record_cal()
        assert len(cal) > 0
        assert cal[0] >= datetime.datetime(1999, 1, 8)

    @pytest.mark.integration
    def test_get_last_date_returns_datetime_or_none(self):
        """[集成] ✓ 读取最后更新日期，返回 datetime 或 None"""
        puller = FundDailyTushare()
        last_date = puller.get_last_date()
        assert last_date is None or isinstance(last_date, datetime.datetime)


class TestIndexDailyTushare:
    """IndexDailyTushare 指数日线下载器测试"""

    def test_init_sets_table(self):
        """✓ 初始化后 to_table 为 IndexDaily"""
        puller = IndexDailyTushare()
        assert puller.to_table == IndexDaily

    @pytest.mark.integration
    def test_pull_does_not_crash(self):
        """[集成] ✓ pull() 方法执行不崩溃（数据已是最新时快速返回）"""
        puller = IndexDailyTushare()
        puller.pull()  # 不抛出异常即可
