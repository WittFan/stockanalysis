"""
因子表达式计算引擎子包

从顶层 datafeed 包的角度向后兼容：
  from datafeed.expr import calc_expr   # 仍然有效
"""
from datafeed.expr.expr import *       # noqa: F401,F403
from datafeed.expr.expr import calc_expr  # noqa: F401
