import numpy as np
import pandas as pd


def shift(se: pd.Series, N):
    return se.shift(N)


def roc(se: pd.Series, N):
    return se / shift(se, N) - 1


def label(se, N):
    res = pd.Series(np.where(se > N, 1, 0))
    res.index = se.index
    return res



def log(se: pd.Series):
    return np.log(se)


def Abs(se):
    return np.abs(se)






















