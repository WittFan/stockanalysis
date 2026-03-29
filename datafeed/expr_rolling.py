import numpy as np
import pandas as pd
from scipy.stats import percentileofscore


def rolling(se, N, func):
    ind = getattr(se.rolling(window=N), func)()
    return ind


def sum(se: pd.Series, N):
    return rolling(se, N, 'sum')


def max(se, N):
    return rolling(se, N, 'max')


def min(se, N):
    return rolling(se, N, 'min')


def std(se, N):
    return rolling(se, N, 'std')


def avg(se, N):
    se = rolling(se, N, 'mean')
    return se


def mean(se, N):
    return avg(se, N)


def idxmax(se, N):
    return se.rolling(N, min_periods=2).apply(lambda x: x.argmax())


def idxmin(se, N):
    return se.rolling(N, min_periods=2).apply(lambda x: x.argmin())


def ts_rank(se, N):
    return se.rolling(N).apply(lambda x: percentileofscore(x, x[-1]) / len(x))


def _zscore(se):
    return se - se.mean() / se.std()


def zscore(se: pd.Series, N):
    return se.rolling(window=N).apply(lambda x: _zscore(x))


def _slope(x):
    try:
        x = x / x.iloc[0]  # 这里做了一个“归一化”
        slope = np.polyfit(range(len(x)), x, 1)[0]
        return slope
    except:
        return -1


def slope(se, N):
    result = se.rolling(N, min_periods=2).apply(lambda x: slope(x))
    return result


def quantile(se, N, qscore):
    return se.rolling(N, min_periods=1).quantile(qscore)


def bias(se, N):
    return se.rolling(N).apply(lambda x: x / x.mean())


def _qcut(se: pd.Series, quantiles, N):
    if len(se) < 3:
        return
    return pd.qcut(se, quantiles, labels=range(0, N), duplicates='drop').astype('float')


def qcut(se: pd.Series, N):
    quantiles = [step / 100 for step in range(0, 100, int(100 / N))]
    if len(quantiles) <= N:
        quantiles.append(1)
    labels = se.rolling(N).apply(
        lambda sub_se: _qcut(sub_se, quantiles, N))
    return labels
