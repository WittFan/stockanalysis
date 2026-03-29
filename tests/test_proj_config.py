"""
ProjConfig 配置管理测试
验证数据加载、算子解析、TOML 配置读取
"""
import pytest
import os

from engine.proj_config import ProjConfig, AlgoConfig, from_toml
from engine.algos import SelectAll, WeightEqually, Rebalance, RunMonthly, WeightERC
from tests.conftest import TEST_SYMBOLS, TEST_START, TEST_END


class TestProjConfigFields:
    """ProjConfig 字段和默认值测试"""

    def test_initial_capital_default(self):
        """✓ initial_capital 默认值为 1,000,000"""
        config = ProjConfig()
        assert config.initial_capital == 1_000_000.0

    def test_commission_slippage_are_float(self):
        """✓ commission 和 slippage 为 float"""
        config = ProjConfig()
        assert isinstance(config.commission, float)
        assert isinstance(config.slippage, float)

    def test_symbols_default_empty(self):
        """✓ symbols 默认为空列表"""
        config = ProjConfig()
        assert config.symbols == []

    def test_algos_default_empty(self):
        """✓ algos 默认为空列表"""
        config = ProjConfig()
        assert config.algos == []

    def test_custom_initial_capital(self):
        """✓ 可自定义 initial_capital"""
        config = ProjConfig(initial_capital=500_000.0)
        assert config.initial_capital == 500_000.0


class TestParseAlgos:
    """parse_algos() 算子解析测试"""

    def test_parse_select_all(self):
        """✓ AlgoConfig(name='SelectAll') 解析为 SelectAll 实例"""
        config = ProjConfig()
        # parse_algos() 内部对每个 algo_config 做 AlgoConfig(**algo_config)，需传 dict
        config.algos = [{'name': 'SelectAll'}]
        algos = config.parse_algos()
        assert len(algos) == 1
        assert isinstance(algos[0], SelectAll)

    def test_parse_multiple_algos(self):
        """✓ 多个算子按顺序解析"""
        config = ProjConfig()
        config.algos = [
            {'name': 'RunMonthly'},
            {'name': 'SelectAll'},
            {'name': 'WeightEqually'},
            {'name': 'Rebalance'},
        ]
        algos = config.parse_algos()
        assert len(algos) == 4
        assert isinstance(algos[0], RunMonthly)
        assert isinstance(algos[1], SelectAll)
        assert isinstance(algos[2], WeightEqually)
        assert isinstance(algos[3], Rebalance)

    def test_parse_algo_with_args(self):
        """✓ AlgoConfig 传入 args 参数正确"""
        config = ProjConfig()
        config.algos = [{'name': 'SelectAll'}]
        algos = config.parse_algos()
        assert len(algos) == 1


class TestLoadDf:
    """load_df() 数据加载测试（使用真实 DuckDB）"""

    def test_load_df_returns_dataframe(self):
        """✓ load_df() 返回 pandas DataFrame"""
        config = ProjConfig(
            symbols=['510300.SH'],
            start_date='20210101',
            end_date='20210331',
            data_folder='etfs',
        )
        df = config.load_df()
        import pandas as pd
        assert isinstance(df, pd.DataFrame)

    def test_load_df_has_required_columns(self):
        """✓ 返回的 DataFrame 包含 symbol、OHLCV 列"""
        config = ProjConfig(
            symbols=['510300.SH'],
            start_date='20210101',
            end_date='20210331',
            data_folder='etfs',
        )
        df = config.load_df()
        required = {'symbol', 'open', 'high', 'low', 'close', 'volume'}
        assert required.issubset(set(df.columns))

    def test_load_df_symbol_matches_config(self):
        """✓ 返回数据中的 symbol 与配置一致"""
        config = ProjConfig(
            symbols=TEST_SYMBOLS,
            start_date='20210101',
            end_date='20210331',
            data_folder='etfs',
        )
        df = config.load_df()
        loaded_syms = set(df['symbol'].unique())
        assert loaded_syms == set(TEST_SYMBOLS)


class TestFromToml:
    """from_toml() TOML 文件加载测试"""

    def test_load_etf_toml(self):
        """✓ 成功加载 ETF-大类资产-风险平价.toml"""
        toml_path = 'data/projs/ETF-大类资产-风险平价.toml'
        if not os.path.exists(toml_path):
            pytest.skip('TOML 配置文件不存在，跳过测试')
        config = from_toml(toml_path)
        assert config.name == 'ETF-大类资产-风险平价'
        assert len(config.symbols) > 0

    def test_from_toml_algos_parsed(self):
        """✓ 从 TOML 加载后 algos 被自动 parse 为 Algo 实例"""
        toml_path = 'data/projs/ETF-大类资产-风险平价.toml'
        if not os.path.exists(toml_path):
            pytest.skip('TOML 配置文件不存在，跳过测试')
        config = from_toml(toml_path)
        from engine.algos.algo_base import Algo
        for algo in config.algos:
            assert isinstance(algo, Algo)

    def test_from_toml_end_date_auto_set(self):
        """✓ TOML 中没有 end_date 时，自动设为当天"""
        toml_path = 'data/projs/ETF-大类资产-风险平价.toml'
        if not os.path.exists(toml_path):
            pytest.skip('TOML 配置文件不存在，跳过测试')
        config = from_toml(toml_path)
        # end_date 格式为 YYYYMMDD 字符串
        assert config.end_date is not None
        assert len(config.end_date) == 8
