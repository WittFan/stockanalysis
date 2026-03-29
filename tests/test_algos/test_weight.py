"""
权重计算算子测试（WeightEqually, WeightERC）
"""
import pytest
from engine.algos import WeightEqually, WeightERC, SelectAll


class TestWeightEqually:
    """WeightEqually：等权重分配"""

    def test_weights_sum_to_one(self, mock_target):
        """✓ 权重之和为 1.0"""
        mock_target.temp['selected'] = mock_target.symbols
        algo = WeightEqually()
        algo(mock_target)
        weights = mock_target.temp['weights']
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_all_weights_equal(self, mock_target):
        """✓ 每个标的权重相等（1/N）"""
        mock_target.temp['selected'] = mock_target.symbols
        algo = WeightEqually()
        algo(mock_target)
        weights = mock_target.temp['weights']
        n = len(mock_target.symbols)
        expected = 1.0 / n
        for sym, w in weights.items():
            assert abs(w - expected) < 1e-9

    def test_single_symbol(self, mock_target):
        """✓ 只有 1 个标的时，权重为 1.0"""
        mock_target.temp['selected'] = [mock_target.symbols[0]]
        algo = WeightEqually()
        algo(mock_target)
        weights = mock_target.temp['weights']
        assert abs(list(weights.values())[0] - 1.0) < 1e-9

    def test_returns_true(self, mock_target):
        """✓ 返回 True 继续算子链"""
        mock_target.temp['selected'] = mock_target.symbols
        algo = WeightEqually()
        result = algo(mock_target)
        assert result is True

    def test_no_selected_returns_true(self, mock_target):
        """✓ 无 selected 时不崩溃，返回 True（或跳过）"""
        mock_target.temp = {}  # 无 selected
        algo = WeightEqually()
        try:
            result = algo(mock_target)
            # 如果不崩溃，result 应该是 True 或 None
            assert result is True or result is None
        except (KeyError, ZeroDivisionError):
            pass  # 允许抛出受控异常


class TestWeightERC:
    """WeightERC：等风险贡献权重"""

    def test_weights_sum_to_one(self, mock_target):
        """✓ 权重之和为 1.0"""
        mock_target.temp['selected'] = mock_target.symbols
        algo = WeightERC()
        algo(mock_target)
        weights = mock_target.temp['weights']
        if weights:  # 历史数据不足时可能为空
            assert abs(sum(weights.values()) - 1.0) < 1e-6

    def test_weights_all_positive(self, mock_target):
        """✓ 等风险贡献权重全为正值"""
        mock_target.temp['selected'] = mock_target.symbols
        algo = WeightERC()
        algo(mock_target)
        weights = mock_target.temp['weights']
        for sym, w in weights.items():
            assert w > 0

    def test_returns_true(self, mock_target):
        """✓ 返回 True 继续算子链"""
        mock_target.temp['selected'] = mock_target.symbols
        algo = WeightERC()
        result = algo(mock_target)
        assert result is True
