import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


# from numba import jit


def pair(left, right, func, *args, **kwargs):
    return func(left, right, *args, **kwargs)


def _corr(left, right, N):
    return pd.Series(left).rolling(window=N).corr(pd.Series(right))


def corr(se_left, se_right, N):
    return pair(se_left, se_right, _corr, N)


def correlation(se_left, se_right, N):
    return corr(se_left, se_right, N)


def greater(left, right):
    if type(right) is not pd.Series:
        right = pd.Series([right for _ in range(len(left))])
        right.index = left.index
    return pair(left, right, np.maximum)


def less(left, right):
    if type(right) is not pd.Series:
        right = pd.Series([right for _ in range(len(left))])
        right.index = left.index
    return pair(left, right, np.minimum)


def _cross_up(left, right):
    left = pd.Series(left)
    right = pd.Series(right)
    diff = left - right
    diff_shift = diff.shift(1)
    return (diff >= 0) & (diff_shift < 0)


def cross_up(left, right):
    return pair(left, right, _cross_up)


def cross_down(left, right):
    def _cross_down(left, right):
        left = pd.Series(left)
        right = pd.Series(right)
        diff = left - right
        diff_shift = diff.shift(1)
        return (diff <= 0) & (diff_shift > 0)

    return pair(left, right, _cross_down)


def _slope_pair(se_left, se_right, N=18):
    slopes = []
    R2 = []
    # 计算斜率值
    for i in range(len(se_left)):
        if i < (N - 1):
            slopes.append(np.nan)
            R2.append(np.nan)
        else:
            x = se_right[i - N + 1:i + 1]
            y = se_left[i - N + 1:i + 1]
            slope, intercept = np.polyfit(x, y, 1)

            # lr = LinearRegression().fit(np.array(x).reshape(-1, 1), y)
            ## y_pred = lr.predict(x.reshape(-1, 1))
            # beta = lr.coef_[0]
            # r2 = r2_score(y, y_pred)
            slopes.append(slope)
            # R2.append(r2)
    slopes = pd.Series(slopes)
    slopes.index = se_left.index
    return slopes


def slope_pair(left, right, N=18):
    return pair(left, right, _slope_pair, N)
