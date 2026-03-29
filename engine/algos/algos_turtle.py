import numpy as np

from .algo_base import Algo
from engine.strategy import BtExecContext as ExecContext


class AlgoTurtle(Algo):
    def __init__(self):
        super(AlgoTurtle, self).__init__()
        self.long_add_point = None
        self.long_stop_loss = None
        self.short_add_point = None
        self.short_stop_loss = None

    def exec(self, se, ctx: ExecContext):

        close = se['close']
        high_N = se['high_N']
        low_N = se['low_N']
        open = se['open']
        ATR = se['atr']
        roc_20 = se['roc_20']
        atr_half = 0.5 * ATR
        market_value = ctx.total_market_value

        if not self.long_add_point:
            self.long_add_point = open + atr_half

        if not self.long_stop_loss:
            self.long_stop_loss = open - atr_half

        if not self.short_add_point:
            self.short_add_point = close - atr_half

        if not self.short_stop_loss:
            self.short_stop_loss = close + atr_half

        if not ctx.long_pos():
            # 如果向上突破唐奇安通道，则开多
            #if close > high_N:
            if roc_20 > 0.08:
                shares = float(market_value) * 0.01 / ATR
                self.long_stop_loss = open - atr_half
                ctx.buy_shares = shares
                #ctx.stop_loss = stop_price
                print('建仓：', shares, ctx.close[-1])

        if ctx.long_pos():

            # if close > self.long_add_point:
            #    ctx.buy_shares = float(market_value)*0.01/ATR
            #    self.long_add_point += atr_half
            #    self.long_stop_loss += atr_half


            


            # 离场信号
            #if close < low_N:
            if roc_20 <0:
                print('平仓：',ctx.close[-1])
                ctx.sell_all_shares()
                return

            # 止损信号
            if close < self.long_stop_loss:
                print('止损', close)
                ctx.sell_all_shares()
                return

                '''

'''
        if ctx.short_pos():
            if close < self.short_add_point:
                ctx.sell_shares = market_value*0.01/ATR
                self.short_add_point -= atr_half
                self.short_stop_loss -= atr_half

            if close > self.short_stop_loss:
                holding = ctx.short_pos().shares
                min_ = min(holding, atr_half)
                ctx.buy_shares = min_

                self.short_add_point += atr_half
                self.short_stop_loss += atr_half


    def __call__(self, target):
        df_bar = target.df_bar
        for symbol, ctx in target.ctxs.items():
            self.exec(df_bar.loc[symbol], ctx)
