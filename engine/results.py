from typing import Optional

import numpy as np
import pandas as pd
from joblib import delayed, Parallel
from loguru import logger
import tqdm
from .ffn_performance import GroupStats


class Result(GroupStats):
    """
    Based on ffn's GroupStats with a few extra helper methods.

    Args:
        * backtests (list): List of backtests

    Attributes:
        * backtest_list (list): List of bactests in the same order as provided
        * backtests (dict): Dict of backtests by name

    """

    def __init__(self, *backtests):
        tmp = [pd.DataFrame({x.name: x.strategy.prices()}) for x in backtests]
        super(Result, self).__init__(*tmp)
        self.backtest_list = backtests
        self.backtests = {x.name: x for x in backtests}

    def display_monthly_returns(self, backtest=0):
        """
        Display monthly returns for a specific backtest.

        Args:
            * backtest (str, int): Backtest. Can be either a index (int) or the
                name (str)

        """
        key = self._get_backtest(backtest)
        self[key].display_monthly_returns()

    def get_weights(self, backtest=0, filter=None):
        """

        :param backtest: (str, int) Backtest can be either a index (int) or the
                name (str)
        :param filter: (list, str) filter columns for specific columns. Filter
                is simply passed as is to DataFrame[filter], so use something
                that makes sense with a DataFrame.
        :return: (pd.DataFrame) DataFrame of weights
        """

        key = self._get_backtest(backtest)

        if filter is not None:
            data = self.backtests[key].weights[filter]
        else:
            data = self.backtests[key].weights

        return data

    def plot_weights(self, backtest=0, filter=None, figsize=(15, 5), **kwds):
        """
        Plots the weights of a given backtest over time.

        Args:
            * backtest (str, int): Backtest can be either a index (int) or the
              name (str)
            * filter (list, str): filter columns for specific columns. Filter
              is simply passed as is to DataFrame[filter], so use something
              that makes sense with a DataFrame.
            * figsize ((width, height)): figure size
            * kwds (dict): Keywords passed to plot

        """
        data = self.get_weights(backtest, filter)

        data.plot(figsize=figsize, **kwds)

    def get_security_weights(self, backtest=0, filter=None):
        """

        :param backtest: (str, int) Backtest can be either a index (int) or the
                name (str)
        :param filter: (list, str) filter columns for specific columns. Filter
                is simply passed as is to DataFrame[filter], so use something
                that makes sense with a DataFrame.
        :return: (pd.DataFrame) DataFrame of security weights
        """

        key = self._get_backtest(backtest)

        if filter is not None:
            data = self.backtests[key].security_weights[filter]
        else:
            data = self.backtests[key].security_weights

        return data

    def plot_security_weights(self, backtest=0, filter=None, figsize=(15, 5), **kwds):
        """
        Plots the security weights of a given backtest over time.

        Args:
            * backtest (str, int): Backtest. Can be either a index (int) or the
                name (str)
            * filter (list, str): filter columns for specific columns. Filter
                is simply passed as is to DataFrame[filter], so use something
                that makes sense with a DataFrame.
            * figsize ((width, height)): figure size
            * kwds (dict): Keywords passed to plot

        """
        data = self.get_security_weights(backtest, filter)

        data.plot(figsize=figsize, **kwds)

    def plot_histogram(self, backtest=0, **kwds):
        """
        Plots the return histogram of a given backtest over time.

        Args:
            * backtest (str, int): Backtest. Can be either a index (int) or the
                name (str)
            * kwds (dict): Keywords passed to plot_histogram

        """
        key = self._get_backtest(backtest)
        self[key].plot_histogram(**kwds)

    def _get_backtest(self, backtest):
        # based on input order
        if type(backtest) == int:
            return self.backtest_list[backtest].name

        # default case assume ok
        return backtest

    def get_transactions(self, strategy_name=None):
        """
        Helper function that returns the transactions in the following format:

            Date, Security | quantity, price

        The result is a MultiIndex DataFrame.

        Args:
            * strategy_name (str): If none, it will take the first backtest's
              strategy (self.backtest_list[0].name)

        """
        if strategy_name is None:
            strategy_name = self.backtest_list[0].name

        # extract strategy given strategy_name
        return self.backtests[strategy_name].strategy.get_transactions()


class Backtest:
    def __init__(self, name, strategy: Strategy, df: pd.DataFrame):
        self.name = name
        self.df_data = df
        self.data = df
        self.df_close = self.df_data.pivot_table(columns='symbol', values='close', index='date')
        self.strategy = strategy
        dates = list(self.df_data.index.unique())
        dates.sort()
        self.dates = dates
        self.index = 0

        self.temp = {}
        self.perm = {}

    def _step(self, date: np.datetime64):
        bar_df = self.df_data.loc[date].copy(deep=True)
        if type(bar_df) is pd.Series:
            bar_df = bar_df.to_frame().T

        symbol_col = 'symbol'
        bar_df.set_index(symbol_col, inplace=True)
        bar_df.sort_index(inplace=True)

        # 这里同时传入收益率序列，也传入整个bar_df
        self.strategy.update_bar(date, bar_df['return_0'])
        return bar_df

    def run(self):
        logger.debug('开始回测:{}到{}，共{}天'.format(self.dates[0], self.dates[-1], len(self.dates)))
        # 这里遍历每一个bar
        for i, date in enumerate(tqdm.tqdm(self.dates)):
            self.temp = {}
            self.index = i
            self.bar_df = self._step(date)
            self.now = date

            self.strategy.run(self)

        logger.debug('回测成功完成！')


def run(*backtests, parallel=True):
    """
    Runs a series of backtests and returns a Result
    object containing the results of the backtests.

    Args:
        * backtest (*list): List of backtests.

    Returns:
        Result

    """

    if parallel == False:
        for bkt in backtests:
            bkt.run()
        return Result(*backtests)

    def run_func(bkt):
        bkt.run()
        return bkt

    tasks = [delayed(run_func)(bkt) for bkt in backtests]
    res = Parallel(n_jobs=len(backtests))(tasks)
    return Result(*res)
