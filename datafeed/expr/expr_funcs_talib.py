import pandas as pd
import talib

# todo 未重构，这个文件请勿使用。
def _ta(fn, se, *args, **kwargs):
    result = getattr(talib, fn)(se, *args)
    if type(result) is tuple:
        if 'get_result' in kwargs.keys():
            if kwargs['get_result'] >= len(result):
                print('参数超过个数，返回第一个')
                return result[0]
            else:
                return result[kwargs['get_result']]
        return result[0]
    return result


def ta(fn, se: pd.Series, *args, **kwargs):
    return se.groupby('symbol', group_keys=False).apply(lambda x: _ta(fn, x, *args, **kwargs))


def sma(se, N):
    return ta('SMA', se, N)


def ema(se, N):
    return ta('EMA', se, N)


def rsi(se, N):
    return ta('RSI', se, N)


def macd(se):
    return ta("MACD", se, get_result=2)


def bbands_up(se):
    return ta('BBANDS', se, get_result=0)


def bbands_down(se):
    return ta('BBANDS', se, get_result=2)


def ta_atr(high, low, close, period=14):
    se = talib.ATR(high, low, close, period)
    se = pd.Series(se)
    se.index = high.index
    return se



def _obv(close, volume):
    return talib.OBV(close, volume)


def ta_obv(close, volume):
    close.name = 'close'
    volume.name = 'volume'
    df = pd.concat([close, volume], axis=1)
    se = df.groupby('symbol', group_keys=False).apply(lambda sub_df: _obv(sub_df['close'], sub_df['volume']))
    if type(se) is pd.DataFrame:
        se = se.T
        se = se[se.columns[0]]
    return se
