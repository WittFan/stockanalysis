"""
数据加载测试（Duckdbloader）
直接查询真实 duck.db，通过限定 symbol + 日期范围控制查询量
"""
import pytest
import pandas as pd

from datafeed.dataloader import Duckdbloader
from tests.conftest import TEST_SYMBOLS, TEST_START, TEST_END


@pytest.fixture(scope='module')
def loaded_df():
    """加载 3 个 ETF 标的的 2021 年数据（约 750 行）"""
    loader = Duckdbloader(
        path='',
        symbols=TEST_SYMBOLS,
        columns=['open', 'high', 'low', 'close', 'volume'],
        start_date=TEST_START,
        end_date=TEST_END,
    )
    return loader.load()


class TestDuckdbloaderLoad:
    """Duckdbloader.load() 基础功能测试"""

    def test_returns_dataframe(self, loaded_df):
        """✓ load() 返回 pandas DataFrame"""
        assert isinstance(loaded_df, pd.DataFrame)

    def test_not_empty(self, loaded_df):
        """✓ 有数据，行数 > 0"""
        assert len(loaded_df) > 0

    def test_required_columns_exist(self, loaded_df):
        """✓ 包含 open, high, low, close, volume, symbol"""
        required = {'open', 'high', 'low', 'close', 'volume', 'symbol'}
        assert required.issubset(set(loaded_df.columns))

    def test_index_is_datetime_like(self, loaded_df):
        """✓ index 为 Timestamp 或 YYYY-MM-DD 格式字符串"""
        first_idx = loaded_df.index[0]
        # Duckdbloader 返回的 index 可能是 Timestamp 或字符串
        idx_str = str(first_idx)[:10]
        assert len(idx_str) == 10
        assert idx_str[4] == '-' and idx_str[7] == '-'

    def test_symbol_column_values(self, loaded_df):
        """✓ symbol 列包含全部请求的标的"""
        loaded_syms = set(loaded_df['symbol'].unique())
        assert loaded_syms == set(TEST_SYMBOLS)

    def test_date_range_within_bounds(self, loaded_df):
        """✓ 数据日期在 start_date 到 end_date 范围内"""
        start_str = TEST_START[:4] + '-' + TEST_START[4:6] + '-' + TEST_START[6:]
        end_str = TEST_END[:4] + '-' + TEST_END[4:6] + '-' + TEST_END[6:]
        # 统一转为字符串比较
        assert str(loaded_df.index.min())[:10] >= start_str
        assert str(loaded_df.index.max())[:10] <= end_str

    def test_sorted_by_date(self, loaded_df):
        """✓ 数据按日期升序排列"""
        dates = loaded_df.index.tolist()
        assert dates == sorted(dates)

    def test_no_negative_close_price(self, loaded_df):
        """✓ 收盘价全为正值（复权后不应为负）"""
        assert (loaded_df['close'] > 0).all()


class TestDuckdbloaderAdjPrice:
    """复权价格计算测试"""

    def test_adj_price_columns_created(self):
        """✓ adj_price() 生成复权列"""
        df = pd.DataFrame({
            'trade_date': pd.date_range('2021-01-04', periods=5),
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [98, 99, 100, 101, 102],
            'close': [101, 102, 103, 104, 105],
            'pre_close': [100, 101, 102, 103, 104],
        })
        result = Duckdbloader.adj_price(df)
        assert 'close_after_adj' in result.columns
        assert 'open_after_adj' in result.columns
        assert 'high_after_adj' in result.columns
        assert 'low_after_adj' in result.columns

    def test_adj_price_first_row_unchanged(self):
        """✓ 第一行收盘价等于原始收盘价（复权基准）"""
        df = pd.DataFrame({
            'trade_date': pd.date_range('2021-01-04', periods=3),
            'open': [100.0, 101.0, 102.0],
            'high': [105.0, 106.0, 107.0],
            'low': [98.0, 99.0, 100.0],
            'close': [101.0, 102.0, 103.0],
            'pre_close': [100.0, 101.0, 102.0],
        })
        result = Duckdbloader.adj_price(df)
        assert abs(result.iloc[0]['close_after_adj'] - 101.0) < 0.01


class TestDuckdbloaderWithFields:
    """带自定义因子字段的加载测试"""

    def test_load_with_roc_field(self):
        """✓ 传入 fields=['roc(close,20)'] 因子列被追加"""
        loader = Duckdbloader(
            path='',
            symbols=['510300.SH'],
            columns=['open', 'high', 'low', 'close', 'volume'],
            start_date='20210101',
            end_date='20211231',
        )
        df = loader.load(fields=['roc(close,20)'], names=['roc_20'])
        assert 'roc_20' in df.columns
        # 前 20 行 NaN 是正常的（窗口期未满）
        assert df['roc_20'].notna().any()
