from types import SimpleNamespace

import backtrader as bt
import pandas as pd
from loguru import logger

from engine.proj_config import ProjConfig
from engine.engine_utils import load_data


class BtExecContext:
    """
    兼容 PyBroker ExecContext 接口的包装类。
    支持 algos_balance（rebalance）和 algos_turtle（直接下单）两种算子的调用方式。
    """
    def __init__(self, strategy, symbol: str):
        self._strategy = strategy
        self.symbol = symbol
        self._data = strategy.getdatabyname(symbol)

    # ---- 持仓查询 ----

    def long_pos(self):
        """返回多头持仓信息，兼容 PyBroker 接口"""
        pos = self._strategy.getposition(self._data)
        if pos.size > 0:
            return SimpleNamespace(shares=pos.size)
        return None

    def short_pos(self):
        """本项目不做空，始终返回 None"""
        return None

    # ---- 下单接口（供 AlgoTurtle 等直接操作 ctx 的算子使用）----

    @property
    def buy_shares(self):
        return 0

    @buy_shares.setter
    def buy_shares(self, shares):
        if shares and shares > 0:
            self._strategy.buy(data=self._data, size=int(shares))

    @property
    def sell_shares(self):
        return 0

    @sell_shares.setter
    def sell_shares(self, shares):
        if shares and shares > 0:
            self._strategy.sell(data=self._data, size=int(shares))

    def sell_all_shares(self):
        """清空当前多头持仓"""
        pos = self._strategy.getposition(self._data)
        if pos.size > 0:
            self._strategy.close(data=self._data)

    # ---- 行情数据 ----

    @property
    def close(self):
        """返回收盘价数组，兼容 ctx.close[-1] 访问方式"""
        return self._data.close.array

    @property
    def total_market_value(self):
        """账户总市值"""
        return self._strategy.broker.getvalue()


class StrategyBase(bt.Strategy):
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        logger.info('%s, %s' % (dt.isoformat(), txt))

    def get_current_dt(self):
        return self.datas[0].datetime.date(0).strftime('%Y-%m-%d')

    def get_current_holding_symbols(self):
        holdings = []
        for name in self.getdatanames():
            data = self.getdatabyname(name)
            if self.getposition(data).size > 0:
                holdings.append(name)
        return holdings

    def get_symbol_mv(self, symbol):
        pos = self.getpositionbyname(symbol)
        return pos.size * pos.price

    def notify_order(self, order):
        order_status = ['Created', 'Submitted', 'Accepted', 'Partial',
                        'Completed', 'Canceled', 'Expired', 'Margin', 'Rejected']
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Partial, order.Completed]:
            if not self.print_order:
                return
            if order.isbuy():
                self.log(
                    '【买入】完成/部分完成, 订单号:%.0f, 标的: %s, 数量: %.2f, 成交价: %.2f, 成交市值: %.2f, 手续费 %.2f' %
                    (order.ref, order.data._name, order.executed.size,
                     order.executed.price, order.executed.value, order.executed.comm))
            else:
                self.log(
                    '卖出完成：订单号:%.0f, 标的: %s, 数量: %.2f, 成交价: %.2f, 卖出市值: %.2f, 交易费用 %.2f' %
                    (order.ref, order.data._name, order.executed.size,
                     order.executed.price, order.executed.value, order.executed.comm))

        elif order.status in [order.Canceled, order.Margin, order.Rejected, order.Expired]:
            self.log('未完成订单，订单号:%.0f, 标的 : %s, 订单状态: %s' % (
                order.ref, order.data._name, order_status[order.status]))

        self.order = None

    def notify_trade(self, trade):
        if trade.justopened:
            return
        elif trade.isclosed:
            return


class StrategyAlgo(StrategyBase):
    """
    Backtrader 策略类，核心是在 next() 中顺序执行算子链（Algo 模式，借鉴自 bt 库）。
    通过 BtExecContext 兼容层保持与现有算子系统的接口兼容。
    """
    params = (
        ('algo_list', []),
        ('engine', None),
        ('global_observer', None),
    )

    def __init__(self):
        self.algos = self.params.algo_list
        self.df_data = self.params.engine.df_data
        self.print_order = False
        self.temp = {}
        self.perm = {}
        self.index = -1
        # 统一 dates 为字符串格式，与 next() 中 self.now 的 strftime 输出一致
        self.dates = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)[:10]
                      for d in self.df_data.index.unique()]
        self.symbols = list(self.df_data['symbol'].unique())
        self.global_observer = self.params.global_observer
        # 回测结束后用于 analysis() 的账户价值序列
        self._portfolio_values = {}

    def global_notify(self, data):
        if self.global_observer:
            self.global_observer.notify(data)

    def next(self):
        self.index += 1
        self.now = self.datas[0].datetime.date(0).strftime('%Y-%m-%d')

        self.global_notify(
            {'msg_type': 'ON_BAR', 'step': self.index,
             'progress': round(self.index / len(self.dates), 2)})

        # 构建执行上下文字典（兼容算子系统的 target.ctxs 接口）
        self.ctxs = {sym: BtExecContext(self, sym) for sym in self.symbols}

        # 计算历史数据切片
        self.df_hist = self.df_data.loc[:self.now]
        self.df_bar = self.df_data.loc[self.now]
        if isinstance(self.df_bar, pd.Series):
            self.df_bar = self.df_bar.to_frame().T
        self.df_bar.set_index('symbol', inplace=True)
        self.df_close = self.df_hist.pivot_table(
            index=self.df_hist.index, values='close', columns='symbol')

        # 记录账户总值
        self._portfolio_values[self.now] = self.broker.getvalue()

        self.temp.clear()
        for algo in self.algos:
            if algo(self) is False:
                return

    def rebalance(self, ctxs: dict, targets: dict):
        """
        按目标权重调仓，使用 Backtrader 原生订单接口。
        targets: {symbol: weight}，权重为占总资产的比例。
        """
        portfolio_value = self.broker.getvalue()
        for symbol in self.symbols:
            data = self.getdatabyname(symbol)
            pos = self.getposition(data)
            if symbol not in targets:
                # 清仓
                if pos.size > 0:
                    self.close(data=data)
            else:
                price = data.close[0]
                if price <= 0:
                    continue
                target_shares = int(portfolio_value * targets[symbol] / price)
                diff = target_shares - pos.size
                if diff > 0:
                    self.buy(data=data, size=diff)
                elif diff < 0:
                    self.sell(data=data, size=-diff)

    def get_long_symbols(self, ctxs):
        """获取当前有多头持仓的 symbol 列表"""
        return [sym for sym in self.symbols
                if self.getposition(self.getdatabyname(sym)).size > 0]

    def get_current_holdings(self, ctxs):
        """返回 (多头列表, 空头列表)，本项目不做空"""
        return self.get_long_symbols(ctxs), []


class Engine:
    """
    回测引擎，封装 Backtrader Cerebro 的配置、执行与结果分析。
    支持通过 global_observer 向 GUI 发送进度通知。
    """
    def __init__(self, config: ProjConfig, global_observer=None):
        self.config = config
        self.df_data = config.load_df()
        self.global_observer = global_observer
        self._strat = None

    def run(self):
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(self.config.initial_capital)
        cerebro.broker.setcommission(commission=self.config.commission)

        # 按 symbol 分拆 DataFrame，逐个添加数据源
        for symbol in self.df_data['symbol'].unique():
            df_sym = (self.df_data[self.df_data['symbol'] == symbol]
                      [['open', 'high', 'low', 'close', 'volume']]
                      .copy())
            df_sym.index = pd.to_datetime(df_sym.index)
            feed = bt.feeds.PandasData(dataname=df_sym)
            cerebro.adddata(feed, name=symbol)

        cerebro.addstrategy(
            StrategyAlgo,
            algo_list=self.config.algos,
            engine=self,
            global_observer=self.global_observer,
        )
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')

        results = cerebro.run()
        self._strat = results[0]
        return results

    def analysis(self, console=True):
        logger.debug('回测完成，开始分析...')

        # 提取日收益率序列
        timereturn = self._strat.analyzers.timereturn.get_analysis()
        returns = pd.Series(timereturn, name='策略')
        equities = (1 + returns).cumprod()

        # 加载基准数据
        benchmark = self.config.benchmark
        if benchmark:
            if benchmark in self.config.symbols:
                df_bench = self.df_data[self.df_data['symbol'] == benchmark]['close'].copy()
            else:
                df_bench = load_data(
                    symbols=[benchmark],
                    start_date=self.config.start_date,
                    end_date=self.config.end_date,
                )['close']
            df_bench.name = benchmark
            df_all = pd.concat([equities, df_bench], axis=1)
        else:
            df_all = pd.DataFrame(equities)

        df_all = (df_all.pct_change() + 1).cumprod()
        df_all.dropna(inplace=True)

        from . import performance
        df_ratios = performance.calc_stats(df_all)
        print(df_ratios)

        from .show_results import ShowResults
        if not console:
            html = ShowResults().show(df_all, df_ratios, pd.DataFrame(), return_html=True)
            if self.global_observer:
                self.global_observer.notify({'msg_type': 'HTML', 'html': html})
        else:
            from bokeh.plotting import show
            layout = ShowResults().show(df_all, df_ratios, pd.DataFrame(), return_html=False)
            show(layout)
