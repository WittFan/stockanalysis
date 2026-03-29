import pandas as pd
try:
    from autogluon.tabular import TabularPredictor
except ImportError:
    TabularPredictor = None  # autogluon 未安装时跳过
from loguru import logger
from .algo_base import Algo


class SelectAll(Algo):
    def __init__(self, include_no_data=False, include_negative=False):
        super(SelectAll, self).__init__()
        self.include_no_data = include_no_data
        self.include_negative = include_negative

    def __call__(self, target):
        target.temp["selected"] = list(target.df_bar.index)
        return True


class SelectThese(Algo):
    def __init__(self, tickers):
        super(SelectThese, self).__init__()
        self.tickers = tickers

    def __call__(self, target):
        '''
        selected = []
        for s in self.tickers:
            if s in target.bar_df.index:
                selected.append(s)

        '''
        # print(self.tickers)
        target.temp['selected'] = self.tickers
        # if len(selected) == 0:
        #    return False
        return True


class SelectBySignal(Algo):
    def __init__(self, rules_buy=[], buy_at_least_count=1, rules_sell=[], sell_at_least_count=1):
        super(SelectBySignal, self).__init__()
        self.rules_buy = rules_buy
        self.rules_sell = rules_sell

        if buy_at_least_count > len(rules_buy):
            buy_at_least_count = len(rules_buy)
        if buy_at_least_count <= 0:
            buy_at_least_count = 1
        self.buy_at_least_count = buy_at_least_count

        if sell_at_least_count > len(rules_sell):
            sell_at_least_count = len(rules_sell)
        if sell_at_least_count <= 0:
            sell_at_least_count = 1
        self.sell_at_least_count = sell_at_least_count

    def _check_if_matched(self, df_bar, rules, at_least_count):
        se_count = pd.Series(index=df_bar.index, data=0)
        for r in rules:
            se_count += df_bar.eval(r)

        matched_items = se_count[(se_count.values >= at_least_count)].index
        return list(matched_items)

    def __call__(self, target):
        df_bar = target.df_bar
        matched_buy = []
        matched_sell = []
        if self.rules_buy and len(self.rules_buy):
            matched_buy = self._check_if_matched(df_bar, self.rules_buy, self.buy_at_least_count)

        if self.rules_sell and len(self.rules_sell):
            matched_sell = self._check_if_matched(df_bar, self.rules_sell, self.sell_at_least_count)

        holdings = target.get_long_symbols(target.ctxs)
        if holdings and len(holdings) > 0:
            matched_buy += holdings

        if matched_sell:
            for sell in matched_sell:
                if sell in matched_buy:
                    matched_buy.remove(sell)

        matched_buy = list(set(matched_buy))
        target.temp['selected'] = matched_buy
        #if len(matched_buy) > 1:
        #    print(matched_buy)
        return True


class SelectTopK(Algo):
    def __init__(self, factor_name='order_by', K=1, drop_top_n=0, b_ascending=False):
        super(SelectTopK, self).__init__()
        self.K = K
        self.drop_top_n = drop_top_n  # 这算是一个魔改，就是把最强的N个弃掉，尤其动量指标，过尤不及。
        self.factor_name = factor_name
        self.b_ascending = b_ascending

    def __call__(self, target):

        key = 'selected'
        df_bar = target.df_bar
        if key not in target.temp.keys():
            selected = list(df_bar.index)
        else:
            selected = target.temp[key]

        ctxs = target.ctxs
        #long_symbols = target.get_long_holding_symbols(ctxs)
        #selected += long_symbols

        factor_sorted = df_bar.sort_values(by=self.factor_name, ascending=self.b_ascending)

        symbols = factor_sorted.index
        # bar_df = bar_df.sort_values(self.order_by, ascending=self.b_ascending)

        ordered = []
        count = 0
        for s in symbols:  # 一定是当天有记录的
            if s in selected:
                count += 1
                if count > self.drop_top_n:
                    ordered.append(s)

                if len(ordered) >= self.K:
                    break

        target.temp[key] = ordered


        return True
