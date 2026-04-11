from .expr_funcs_pair import *
try:
    from .expr_funcs_talib import *
except ImportError:
    pass  # TA-Lib 未安装或架构不兼容时跳过
from .expr_funcs import *
from .expr_rolling import *


def expr_transform(df, expr):
    # close/shift(close,5) -1
    for col in df.columns:
        # expr = expr.replace("(" + col, '(df[["symbol","{}"]]'.format(col))
        expr = expr.replace(col, 'df["{}"]'.format(col))
    return expr


def calc_expr(df: pd.DataFrame, expr: str):
    if expr in list(df.columns):
        return df[expr]

    expr = expr_transform(df, expr)

    try:
        se = eval(expr)
        return se
    except:
        import traceback
        traceback.print_exc()
        raise NameError('{}——eval异常'.format(expr))
    # shift(close,1) -> shift(df['close'],1)
    return None
