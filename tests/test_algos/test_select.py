"""
选股算子测试（SelectAll 等）
"""
from engine.algos import SelectAll


class TestSelectAll:
    """SelectAll 算子：选择所有标的"""

    def test_returns_true(self, mock_target):
        """✓ SelectAll() 返回 True，不中断算子链"""
        algo = SelectAll()
        result = algo(mock_target)
        assert result is True

    def test_selected_contains_all_symbols(self, mock_target):
        """✓ temp['selected'] 包含所有 symbols"""
        algo = SelectAll()
        algo(mock_target)
        assert set(mock_target.temp['selected']) == set(mock_target.symbols)

    def test_selected_order_matches_df_bar_index(self, mock_target):
        """✓ temp['selected'] 与 df_bar.index 一致"""
        algo = SelectAll()
        algo(mock_target)
        assert mock_target.temp['selected'] == list(mock_target.df_bar.index)
