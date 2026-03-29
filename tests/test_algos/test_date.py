"""
时间控制算子测试（RunOnce, RunMonthly, RunWeekly 等）
注意：RunPeriod 子类依赖 target.dates、target.index、target.df_data.index
"""
import pandas as pd
from unittest.mock import MagicMock
from engine.algos import RunMonthly, RunWeekly, RunDaily
from engine.algos.algos_date import RunOnce


def make_monthly_target(months=3):
    """构造包含多月交易日历的 MockTarget"""
    target = MagicMock()
    # 生成 3 个月的工作日日期
    dates = list(pd.date_range('2021-01-04', periods=months * 22, freq='B').strftime('%Y-%m-%d'))
    target.dates = dates
    # df_data.index 与 dates 对应（RunPeriod 用来判断 last date）
    target.df_data = MagicMock()
    target.df_data.index = dates
    target.temp = {}
    target.perm = {}
    return target


class TestRunOnce:
    """RunOnce：只运行一次"""

    def test_first_call_returns_true(self):
        """✓ 第一次调用返回 True"""
        target = MagicMock()
        algo = RunOnce()
        assert algo(target) is True

    def test_second_call_returns_false(self):
        """✓ 第二次调用返回 False"""
        target = MagicMock()
        algo = RunOnce()
        algo(target)
        assert algo(target) is False

    def test_subsequent_calls_return_false(self):
        """✓ 多次调用后持续返回 False"""
        target = MagicMock()
        algo = RunOnce()
        algo(target)
        for _ in range(5):
            assert algo(target) is False


class TestRunMonthly:
    """RunMonthly：月初执行一次"""

    def test_returns_true_on_month_start(self):
        """✓ 月份切换时（新月首个交易日）返回 True"""
        target = make_monthly_target(months=3)
        algo = RunMonthly()
        # 找一个月份切换点
        # dates[0]=1月, dates[1]=1月... 找到2月第一个交易日
        found_month_change = False
        for i in range(1, len(target.dates) - 1):
            target.index = i
            target.now = target.dates[i]
            result = algo(target)
            prev_month = pd.Timestamp(target.dates[i - 1]).month
            curr_month = pd.Timestamp(target.dates[i]).month
            if curr_month != prev_month:
                found_month_change = True
                assert result is True
                break
        assert found_month_change, '测试数据中没有月份切换点'

    def test_returns_false_mid_month(self):
        """✓ 月中（非月份切换日）返回 False"""
        target = make_monthly_target(months=2)
        algo = RunMonthly()
        # 选一个确定在月中的日期（不是月份切换点）
        # 从第 2 天开始找第一个月内的非切换点
        for i in range(2, min(10, len(target.dates) - 1)):
            target.index = i
            target.now = target.dates[i]
            prev_month = pd.Timestamp(target.dates[i - 1]).month
            curr_month = pd.Timestamp(target.dates[i]).month
            if curr_month == prev_month:  # 确认是月中
                result = algo(target)
                assert result is False
                return
        # 如果全是月份切换点（不太可能），跳过
        assert True

    def test_returns_false_when_now_is_none(self):
        """✓ target.now 为 None 时返回 False"""
        target = make_monthly_target()
        target.now = None
        target.index = 5
        algo = RunMonthly()
        assert algo(target) is False


class TestRunWeekly:
    """RunWeekly：周初执行一次"""

    def test_returns_true_on_week_start(self):
        """✓ 周份切换时（新周第一个交易日）返回 True"""
        target = make_monthly_target(months=2)
        algo = RunWeekly()
        found_week_change = False
        for i in range(1, len(target.dates) - 1):
            target.index = i
            target.now = target.dates[i]
            result = algo(target)
            prev_week = pd.Timestamp(target.dates[i - 1]).isocalendar()[1]
            curr_week = pd.Timestamp(target.dates[i]).isocalendar()[1]
            if curr_week != prev_week:
                found_week_change = True
                assert result is True
                break
        assert found_week_change, '测试数据中没有周切换点'
