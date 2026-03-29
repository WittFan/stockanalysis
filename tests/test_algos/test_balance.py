"""
再平衡算子测试（Rebalance）
"""
import pandas as pd
from unittest.mock import MagicMock, call
from engine.algos import Rebalance


class TestRebalance:
    """Rebalance 算子：按 weights 调用 target.rebalance()"""

    def test_returns_true(self, mock_target):
        """✓ Rebalance 返回 True"""
        mock_target.temp['weights'] = {'510300.SH': 0.5, '159915.SZ': 0.3, '511220.SH': 0.2}
        algo = Rebalance()
        result = algo(mock_target)
        assert result is True

    def test_calls_target_rebalance(self, mock_target):
        """✓ 调用 target.rebalance(ctxs, targets)"""
        weights = {'510300.SH': 0.5, '159915.SZ': 0.3, '511220.SH': 0.2}
        mock_target.temp['weights'] = weights
        algo = Rebalance()
        algo(mock_target)
        mock_target.rebalance.assert_called_once()

    def test_rebalance_passes_correct_weights(self, mock_target):
        """✓ 传给 rebalance() 的权重字典正确"""
        weights = {'510300.SH': 0.5, '159915.SZ': 0.3, '511220.SH': 0.2}
        mock_target.temp['weights'] = weights
        algo = Rebalance()
        algo(mock_target)
        args = mock_target.rebalance.call_args
        passed_weights = args[0][1]  # 第二个位置参数
        assert passed_weights == weights

    def test_series_weights_converted_to_dict(self, mock_target):
        """✓ pd.Series 权重自动转为 dict"""
        weights_series = pd.Series({'510300.SH': 0.4, '159915.SZ': 0.3, '511220.SH': 0.3})
        mock_target.temp['weights'] = weights_series
        algo = Rebalance()
        algo(mock_target)
        args = mock_target.rebalance.call_args
        passed_weights = args[0][1]
        assert isinstance(passed_weights, dict)

    def test_no_weights_skips_rebalance(self, mock_target):
        """✓ temp 中没有 weights 时，不调用 target.rebalance()，返回 True"""
        mock_target.temp = {}  # 无 weights
        algo = Rebalance()
        result = algo(mock_target)
        assert result is True
        mock_target.rebalance.assert_not_called()
