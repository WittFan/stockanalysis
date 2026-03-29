#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QMTData — Backtrader DataFeed 层，提供 QMT 行情数据。

职责：
1. 实现 Backtrader DataBase 的 _load() 状态机
2. 通过 xtdata 回填历史数据（_ST_HIST）
3. 通过 xtdata.subscribe_quote 接收实时数据（_ST_LIVE）
"""

import threading
from datetime import datetime, timedelta

from loguru import logger

from backtrader.feed import DataBase
from backtrader import date2num, num2date
from backtrader.metabase import MetaParams
from backtrader.utils.py3 import queue


# ────────────────────────────────────────────────
# MetaQMTData：自动将 QMTData 注册到 QMTStore.DataCls
# ────────────────────────────────────────────────

class MetaQMTData(DataBase.__class__):
    """元类：自动将 QMTData 注册为 QMTStore 的 DataCls"""
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        if cls.__name__ == 'QMTData':
            from . import qmtstore
            qmtstore.QMTStore.DataCls = cls


# ────────────────────────────────────────────────
# QMTData
# ────────────────────────────────────────────────

class QMTData(DataBase, metaclass=MetaQMTData):
    """
    Backtrader DataFeed 实现，从 QMT 获取行情数据。

    状态机::

        _ST_START → _ST_HIST → _ST_LIVE → _ST_OVER

    用法::

        store = QMTStore(...)
        data = store.getdata(dataname='511220.SH', backfill_days=30)
        cerebro.adddata(data)
    """

    # 状态常量
    _ST_START = 0    # 初始化
    _ST_HIST = 1     # 回填历史数据
    _ST_LIVE = 2     # 实时数据
    _ST_OVER = 3     # 结束

    params = (
        ('qcheck', 0.5),           # 实时数据队列检查间隔（秒）
        ('backfill', True),        # 是否回填历史数据
        ('backfill_days', 5),      # 回填天数
        ('period', '1d'),          # K线周期
        ('dividend_type', 'none'), # 复权方式: none/front/back
        ('store', None),           # QMTStore 实例（由 getdata 传入）
    )

    # Backtrader DataBase 的 LIVE 通知常量
    LIVE = DataBase.LIVE if hasattr(DataBase, 'LIVE') else 0

    def __init__(self, **kwargs):
        # 从 kwargs 提取 store（如果有）
        store = kwargs.pop('store', None)
        super().__init__(**kwargs)

        if store is not None:
            self.p.store = store

        self._store = self.p.store
        self._state = self._ST_START

        # 实时数据队列
        self.qlive = queue.Queue()

        # 历史数据缓冲
        self._hist_bars = []
        self._hist_idx = 0

        # xtdata 订阅号
        self._subscribe_seq = None

        # xtdata.run() 后台线程（真实 live 模式）
        self._xtdata_thread = None

    def start(self):
        """DataFeed 启动"""
        super().start()
        if self._store is not None:
            self._store.start(data=self)

    def stop(self):
        """DataFeed 停止，取消订阅"""
        super().stop()
        if self._subscribe_seq is not None:
            try:
                self._get_xtdata().unsubscribe_quote(self._subscribe_seq)
            except Exception as e:
                logger.debug(f'取消订阅异常: {e}')
        # xtdata 后台线程是 daemon，主进程结束时自动退出，无需 join

    def islive(self):
        """标记为 live 数据源"""
        return True

    def _load(self):
        """
        Backtrader DataBase 核心方法，返回:
        - True: 成功加载一条数据
        - False: 数据结束
        - None: 暂无数据（live 模式等待中）
        """
        if self._state == self._ST_START:
            return self._load_start()
        elif self._state == self._ST_HIST:
            return self._load_hist()
        elif self._state == self._ST_LIVE:
            return self._load_live()
        else:
            return False  # _ST_OVER

    def _load_start(self):
        """初始化阶段：加载历史数据"""
        if self.p.backfill:
            self._fetch_history()

        if self._hist_bars:
            self._state = self._ST_HIST
            return self._load_hist()
        else:
            # 无历史数据，直接进入 live
            self._state = self._ST_LIVE
            self._subscribe_live()
            self.put_notification(self.LIVE)
            return self._load_live()

    def _load_hist(self):
        """历史数据阶段：逐条弹出缓冲"""
        if self._hist_idx < len(self._hist_bars):
            bar = self._hist_bars[self._hist_idx]
            self._hist_idx += 1
            return self._fill_bar(bar)

        # 历史数据回放完毕 → 切换到 live
        self._hist_bars = []
        self._hist_idx = 0
        self._state = self._ST_LIVE
        self._subscribe_live()
        self.put_notification(self.LIVE)
        logger.info(f'{self.p.dataname}: 历史数据回填完毕，切换到实时模式')
        return self._load_live()

    def _load_live(self):
        """实时数据阶段：从队列获取"""
        try:
            bar = self.qlive.get(timeout=self.p.qcheck)
            return self._fill_bar(bar)
        except queue.Empty:
            return None  # 暂无数据，但仍在线

    # ────────── 历史数据获取 ──────────

    def _fetch_history(self):
        """通过 xtdata 获取历史 K 线数据"""
        xtdata = self._get_xtdata()
        stock_code = self.p.dataname

        end_time = datetime.now().strftime('%Y%m%d')
        start_time = (datetime.now() - timedelta(days=self.p.backfill_days)).strftime('%Y%m%d')

        logger.info(f'{stock_code}: 正在获取历史数据 ({start_time} ~ {end_time}, '
                    f'period={self.p.period})')

        try:
            # xtdata.get_market_data 返回格式:
            # {field: DataFrame(index=stock_list, columns=time_list)}
            data = xtdata.get_market_data(
                field_list=['open', 'high', 'low', 'close', 'volume'],
                stock_list=[stock_code],
                period=self.p.period,
                start_time=start_time,
                end_time=end_time,
                dividend_type=self.p.dividend_type,
                fill_data=True,
            )

            if data is None or not data:
                logger.warning(f'{stock_code}: 未获取到历史数据')
                return

            # 解析数据，构造 bar 列表
            bars = self._parse_xtdata_history(data, stock_code)
            self._hist_bars = bars
            logger.info(f'{stock_code}: 获取到 {len(bars)} 条历史数据')

        except Exception as e:
            logger.error(f'{stock_code}: 获取历史数据失败: {e}')

    def _parse_xtdata_history(self, data, stock_code):
        """
        解析 xtdata.get_market_data 返回的数据。
        返回: [{datetime, open, high, low, close, volume}, ...]
        """
        bars = []

        # data 格式: {field_name: DataFrame(index=stock_list, columns=timestamps)}
        # 获取时间轴
        first_field = next(iter(data.values()), None)
        if first_field is None:
            return bars

        # 判断是 DataFrame 还是其他格式
        if hasattr(first_field, 'columns'):
            timestamps = list(first_field.columns)
        elif hasattr(first_field, 'keys'):
            timestamps = sorted(first_field.keys())
        else:
            return bars

        for ts in timestamps:
            try:
                bar = {}

                # 解析时间戳
                if isinstance(ts, str):
                    if len(ts) == 8:  # '20230101'
                        bar['datetime'] = datetime.strptime(ts, '%Y%m%d')
                    elif len(ts) == 14:  # '20230101093000'
                        bar['datetime'] = datetime.strptime(ts, '%Y%m%d%H%M%S')
                    else:
                        bar['datetime'] = datetime.strptime(str(ts)[:8], '%Y%m%d')
                elif isinstance(ts, (int, float)):
                    # 毫秒时间戳
                    bar['datetime'] = datetime.fromtimestamp(ts / 1000)
                else:
                    bar['datetime'] = datetime.strptime(str(ts)[:8], '%Y%m%d')

                for field in ['open', 'high', 'low', 'close', 'volume']:
                    if field in data:
                        df = data[field]
                        if hasattr(df, 'loc'):
                            val = df.loc[stock_code, ts] if stock_code in df.index else 0.0
                        else:
                            val = 0.0
                        bar[field] = float(val)
                    else:
                        bar[field] = 0.0

                # 跳过无效数据
                if bar['close'] > 0:
                    bars.append(bar)

            except Exception as e:
                logger.debug(f'解析历史 bar 异常: {ts}, {e}')
                continue

        return bars

    # ────────── 实时数据订阅 ──────────

    def _subscribe_live(self):
        """
        订阅实时行情。
        真实 QMT 环境下，subscribe_quote 本身不推送数据，
        需要在独立线程中调用 xtdata.run() 启动事件循环才能触发回调。
        Mock 模式下 subscribe_quote 返回 -1，不启动 run 线程。
        """
        xtdata = self._get_xtdata()
        stock_code = self.p.dataname
        use_mock = self._store and self._store.p.use_mock

        try:
            if self.p.period == 'tick':
                # Tick 数据使用 subscribe_whole_quote（全推）
                self._subscribe_seq = xtdata.subscribe_whole_quote(
                    [stock_code],
                    callback=self._on_quote,
                )
            else:
                # K 线周期使用 subscribe_quote
                self._subscribe_seq = xtdata.subscribe_quote(
                    stock_code,
                    period=self.p.period,
                    callback=self._on_quote,
                )

            if self._subscribe_seq and self._subscribe_seq > 0:
                logger.info(f'{stock_code}: 已订阅行情 period={self.p.period} '
                            f'(seq={self._subscribe_seq})')
                # 真实环境：启动 xtdata.run() 后台线程（全局只需一个，多 datafeed 共用）
                if not use_mock:
                    self._start_xtdata_run(xtdata)
            else:
                logger.warning(f'{stock_code}: 订阅行情失败 (seq={self._subscribe_seq})')
        except Exception as e:
            logger.warning(f'{stock_code}: 订阅异常: {e}')

    def _start_xtdata_run(self, xtdata):
        """
        在后台守护线程中启动 xtdata.run()。
        xtdata.run() 阻塞并持续分发行情推送回调，必须运行在独立线程。
        同一进程内已有线程时跳过重复启动。
        """
        if self._xtdata_thread is not None and self._xtdata_thread.is_alive():
            return  # 已在运行

        def _run():
            logger.info(f'[QMTData] xtdata.run() 后台线程启动')
            try:
                xtdata.run()
            except Exception as e:
                logger.error(f'[QMTData] xtdata.run() 异常退出: {e}')

        self._xtdata_thread = threading.Thread(
            target=_run,
            name='xtdata-run',
            daemon=True,   # 主进程退出时自动销毁
        )
        self._xtdata_thread.start()

    def _on_quote(self, datas):
        """
        xtdata 行情推送回调（K 线周期 / tick 通用入口）。
        datas 格式：
          K线: {stock_code: [bar_dict, ...]} 或 {stock_code: bar_dict}
          Tick: {stock_code: tick_dict}  （subscribe_whole_quote 推送）
        """
        stock_code = self.p.dataname

        try:
            stock_data = datas.get(stock_code)
            if stock_data is None:
                return

            if self.p.period == 'tick':
                # Tick 数据：直接解析单条
                bar = self._parse_tick_item(stock_data)
                if bar:
                    self.qlive.put(bar)
            elif isinstance(stock_data, list):
                for item in stock_data:
                    bar = self._parse_quote_item(item)
                    if bar:
                        self.qlive.put(bar)
            elif isinstance(stock_data, dict):
                bar = self._parse_quote_item(stock_data)
                if bar:
                    self.qlive.put(bar)
            else:
                logger.debug(f'收到未知格式行情推送: {type(stock_data)}')

        except Exception as e:
            logger.error(f'行情推送处理异常: {e}')

    def _parse_quote_item(self, item):
        """解析单条 K 线行情推送，返回 bar dict 或 None"""
        if not isinstance(item, dict):
            return None

        bar = {
            'datetime': datetime.now(),
            'open':   float(item.get('open', 0)),
            'high':   float(item.get('high', 0)),
            'low':    float(item.get('low', 0)),
            'close':  float(item.get('close', item.get('lastPrice', 0))),
            'volume': float(item.get('volume', 0)),
        }
        # 尝试解析时间戳
        if 'time' in item:
            try:
                ts = item['time']
                if isinstance(ts, (int, float)):
                    # xtdata 时间戳单位为毫秒
                    bar['datetime'] = datetime.fromtimestamp(ts / 1000)
                elif isinstance(ts, str):
                    bar['datetime'] = datetime.strptime(ts[:14], '%Y%m%d%H%M%S')
            except Exception:
                pass

        return bar if bar['close'] > 0 else None

    def _parse_tick_item(self, item):
        """
        解析 Tick 行情数据（subscribe_whole_quote 推送格式）。

        xtdata tick 字段（部分）::

            {
              'lastPrice':  12.34,   # 最新价（用作 close）
              'open':       12.00,
              'high':       12.50,
              'low':        11.90,
              'volume':     100000,  # 累计成交量（手）
              'amount':     1234000, # 累计成交金额
              'bidPrice':   [12.33, ...],
              'askPrice':   [12.35, ...],
              'time':       20230901093000,  # int，格式 YYYYMMDDHHmmss
            }
        """
        if not isinstance(item, dict):
            return None

        last_price = float(item.get('lastPrice', 0))
        if last_price <= 0:
            return None

        bar = {
            'datetime': datetime.now(),
            'open':   float(item.get('open', last_price)),
            'high':   float(item.get('high', last_price)),
            'low':    float(item.get('low', last_price)),
            'close':  last_price,
            'volume': float(item.get('volume', item.get('amount', 0))),
        }

        # 解析时间（xtdata tick time 为整数 YYYYMMDDHHmmss）
        ts = item.get('time')
        if ts is not None:
            try:
                if isinstance(ts, (int, float)) and ts > 1e12:
                    # 毫秒时间戳
                    bar['datetime'] = datetime.fromtimestamp(ts / 1000)
                elif isinstance(ts, (int, float)):
                    # YYYYMMDDHHmmss 整数
                    bar['datetime'] = datetime.strptime(str(int(ts)), '%Y%m%d%H%M%S')
                elif isinstance(ts, str):
                    bar['datetime'] = datetime.strptime(ts[:14], '%Y%m%d%H%M%S')
            except Exception:
                pass

        return bar

    # ────────── 填充 Backtrader lines ──────────

    def _fill_bar(self, bar):
        """将 bar dict 填充到 Backtrader lines，返回 True"""
        self.lines.datetime[0] = date2num(bar['datetime'])
        self.lines.open[0] = bar['open']
        self.lines.high[0] = bar['high']
        self.lines.low[0] = bar['low']
        self.lines.close[0] = bar['close']
        self.lines.volume[0] = bar['volume']
        self.lines.openinterest[0] = 0.0
        return True

    # ────────── 工具方法 ──────────

    def _get_xtdata(self):
        """获取 xtdata 模块（支持 mock）"""
        if self._store and self._store.p.use_mock:
            from .mock import MockXtData
            return MockXtData()
        try:
            from xtquant import xtdata
            return xtdata
        except ImportError:
            from .mock import MockXtData
            logger.warning('xtquant 未安装，回退到 MockXtData')
            return MockXtData()
