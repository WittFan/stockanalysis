import numpy as np

from .algo_base import Algo


class AlgoGrid(Algo):
    def __init__(self):
        self.perc_levels = [x for x in np.arange(
            1 + 0.005 * 5, 1 - 0.005 * 5 - 0.005 / 2, -0.005)]
        self.last_price_index = None

    def __call__(self, target):
        df_bar = target.df_bar
        mid = df_bar['mid']['B0']
        close = df_bar['close']['B0']
        price_levels = [mid * x for x in self.perc_levels]
        signal = False
        curr_price_index = None
        for i in range(len(price_levels)):
            if close > price_levels[i]:
                curr_price_index = i
                break
        if not curr_price_index:
            return False

        if self.last_price_index is None:
            signal = True
        else:
            if curr_price_index != self.last_price_index:
                signal = True

        if signal:
            target.order_target_percent(
                target=curr_price_index / (len(price_levels) - 1))
            self.last_price_index = curr_price_index
        return False