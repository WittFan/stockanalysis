# XtQuant.XtTrader 交易模块 API 参考

## 概述

- XtQuant 封装了策略交易所需的 Python API 接口
- 可以和 MiniQMT 客户端交互进行报单、撤单、查询资产、查询持仓等
- 需要先启动 MiniQMT 客户端
- 支持 Python 3.6 / 3.7 / 3.8

## 快速入门

```python
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant

# 创建 API 实例
path = 'D:\\迅投极速交易终端\\userdata_mini'
session_id = 123456
xt_trader = XtQuantTrader(path, session_id)

# 注册回调
callback = MyXtQuantTraderCallback()
xt_trader.register_callback(callback)

# 启动并连接
xt_trader.start()
connect_result = xt_trader.connect()

# 创建账号
acc = StockAccount('1000000365')

# 订阅账号信息
xt_trader.subscribe(acc)

# 下单
order_id = xt_trader.order_stock(
    acc, '600000.SH', xtconstant.STOCK_BUY,
    200, xtconstant.FIX_PRICE, 10.5,
    'strategy1', 'remark'
)

# 阻塞线程
xt_trader.run_forever()
```

## 系统设置接口

### XtQuantTrader(path, session_id)

- `path`: MiniQMT 客户端 `userdata_mini` 完整路径
- `session_id`: 会话 ID，不同策略需使用不同 ID

### register_callback(callback)

- 注册 `XtQuantTraderCallback` 回调实例

### start()

- 启动交易线程

### connect()

- 连接 MiniQMT，返回 `0` 成功，非 `0` 失败
- 一次性连接，断开不会自动重连

### stop()

- 停止 API

### run_forever()

- 阻塞当前线程，直到 `stop()` 被调用

### set_relaxed_response_order_enabled(enabled)

- 控制是否从专用线程返回，获得宽松数据时序

## 操作接口

### subscribe(account) / unsubscribe(account)

- 订阅 / 反订阅账号信息（资金、委托、成交、持仓）
- 返回 `0` 成功，`-1` 失败

### order_stock(account, stock_code, order_type, order_volume, price_type, price, strategy_name, order_remark)

- 同步下单
- `order_type`: `xtconstant.STOCK_BUY` / `STOCK_SELL`
- `order_volume`: 股票以"股"为单位
- `price_type`: `xtconstant.FIX_PRICE` / `LATEST_PRICE`
- 返回: 订单编号（`>0` 成功，`-1` 失败）

### order_stock_async(account, stock_code, order_type, order_volume, price_type, price, strategy_name, order_remark)

- 异步下单，返回 seq 序号（`>0` 成功）
- 通过 `on_order_stock_async_response` 回调获取反馈

### cancel_order_stock(account, order_id)

- 同步撤单（按订单编号）
- 返回 `0` 成功，`-1` 失败

### cancel_order_stock_sysid(account, market, order_sysid)

- 同步撤单（按柜台合同编号）
- `market`: `xtconstant.SH_MARKET` / `SZ_MARKET`

### cancel_order_stock_async(account, order_id)

- 异步撤单（按订单编号）

### cancel_order_stock_sysid_async(account, market, order_sysid)

- 异步撤单（按柜台合同编号）

### fund_transfer(account, transfer_direction, price)

- 资金划拨
- 返回 `(success, msg)`

## 查询接口

### query_stock_asset(account)

- 查询资产，返回 `XtAsset` 或 `None`

### query_stock_orders(account, cancelable_only=False)

- 查询当日委托，返回 `[XtOrder]` 或 `None`

### query_stock_trades(account)

- 查询当日成交，返回 `[XtTrade]` 或 `None`

### query_stock_positions(account)

- 查询持仓，返回 `[XtPosition]` 或 `None`

### query_credit_detail(account)

- 信用资产查询

### query_stk_compacts(account)

- 负债合约查询

### query_credit_subjects(account)

- 融资融券标的查询

### query_credit_slo_code(account)

- 可融券数据查询

### query_credit_assure(account)

- 标的担保品查询

### query_new_purchase_limit(account)

- 新股申购额度查询

### query_ipo_data()

- 当日新股信息查询

### query_account_infos()

- 所有账号信息查询

### query_com_fund(account)

- 普通柜台资金查询

### query_com_position(account)

- 普通柜台持仓查询

## 约券相关接口

### smt_query_quoter(account)

- 券源行情查询

### smt_negotiate_order_async(...)

- 库存券约券申请

### smt_query_compact(account)

- 约券合约查询

## 数据字典

### 交易市场 (market)

- `xtconstant.SH_MARKET` — 上海市场
- `xtconstant.SZ_MARKET` — 深圳市场

### 账号类型 (account_type)

- `FUTURE_ACCOUNT` — 期货账号
- `SECURITY_ACCOUNT` — 证券账号
- `CREDIT_ACCOUNT` — 信用账号
- `STOCK_OPTION_ACCOUNT` — 股票期权账号
- `HUGANGTONG_ACCOUNT` — 沪港通账号
- `SHENGANGTONG_ACCOUNT` — 深港通账号

### 委托类型 (order_type) — 股票

- `STOCK_BUY` — 买入
- `STOCK_SELL` — 卖出

### 报价类型 (price_type)

- `LATEST_PRICE` — 最新价
- `FIX_PRICE` — 指定价
- `MARKET_SH_CONVERT_5_CANCEL` — 上交所五档即成剩撤
- `MARKET_SH_CONVERT_5_LIMIT` — 上交所五档即成剩转限
- `MARKET_PEER_PRICE_FIRST` — 对手方最优价格
- `MARKET_MINE_PRICE_FIRST` — 本方最优价格

### 委托状态 (order_status)

| 枚举 | 值 | 含义 |
|------|-----|------|
| `ORDER_UNREPORTED` | 48 | 未报 |
| `ORDER_WAIT_REPORTING` | 49 | 待报 |
| `ORDER_REPORTED` | 50 | 已报 |
| `ORDER_REPORTED_CANCEL` | 51 | 已报待撤 |
| `ORDER_PARTSUCC_CANCEL` | 52 | 部成待撤 |
| `ORDER_PART_CANCEL` | 53 | 部撤 |
| `ORDER_CANCELED` | 54 | 已撤 |
| `ORDER_PART_SUCC` | 55 | 部成 |
| `ORDER_SUCCEEDED` | 56 | 已成 |
| `ORDER_JUNK` | 57 | 废单 |
| `ORDER_UNKNOWN` | 255 | 未知 |

### 账号状态 (account_status)

| 枚举 | 值 | 含义 |
|------|-----|------|
| `ACCOUNT_STATUS_OK` | 0 | 正常 |
| `ACCOUNT_STATUS_WAITING_LOGIN` | 1 | 连接中 |
| `ACCOUNT_STATUS_FAIL` | 3 | 失败 |
| `ACCOUNT_STATUS_CLOSED` | 6 | 收盘后 |

## 数据结构

### XtAsset

| 属性 | 类型 | 说明 |
|------|------|------|
| `account_type` | int | 账号类型 |
| `account_id` | str | 资金账号 |
| `cash` | float | 可用金额 |
| `frozen_cash` | float | 冻结金额 |
| `market_value` | float | 持仓市值 |
| `total_asset` | float | 总资产 |

### XtOrder

| 属性 | 类型 | 说明 |
|------|------|------|
| `account_id` | str | 资金账号 |
| `stock_code` | str | 证券代码 |
| `order_id` | int | 订单编号 |
| `order_sysid` | str | 柜台合同编号 |
| `order_type` | int | 委托类型 |
| `order_volume` | int | 委托数量 |
| `price_type` | int | 报价类型 |
| `price` | float | 委托价格 |
| `traded_volume` | int | 成交数量 |
| `traded_price` | float | 成交均价 |
| `order_status` | int | 委托状态 |
| `status_msg` | str | 状态描述 |
| `strategy_name` | str | 策略名称 |
| `order_remark` | str | 委托备注 |

### XtTrade

| 属性 | 类型 | 说明 |
|------|------|------|
| `account_id` | str | 资金账号 |
| `stock_code` | str | 证券代码 |
| `traded_id` | str | 成交编号 |
| `traded_time` | int | 成交时间 |
| `traded_price` | float | 成交均价 |
| `traded_volume` | int | 成交数量 |
| `traded_amount` | float | 成交金额 |
| `order_id` | int | 订单编号 |
| `strategy_name` | str | 策略名称 |

### XtPosition

| 属性 | 类型 | 说明 |
|------|------|------|
| `account_id` | str | 资金账号 |
| `stock_code` | str | 证券代码 |
| `volume` | int | 持仓数量 |
| `can_use_volume` | int | 可用数量 |
| `open_price` | float | 开仓价 |
| `market_value` | float | 市值 |
| `frozen_volume` | int | 冻结数量 |
| `on_road_volume` | int | 在途股份 |
| `yesterday_volume` | int | 昨夜拥股 |
| `avg_price` | float | 成本价 |

### XtOrderResponse (异步下单反馈)

- `account_type` — 账号类型
- `account_id` — 资金账号
- `order_id` — 订单编号
- `strategy_name` — 策略名称
- `order_remark` — 委托备注
- `seq` — 序号

### XtOrderError

- `account_type` — 账号类型
- `account_id` — 资金账号
- `order_id` — 订单编号
- `error_id` — 错误代码
- `error_msg` — 错误信息
- `strategy_name` — 策略名称

### XtCancelError

- `account_type` — 账号类型
- `account_id` — 资金账号
- `order_id` — 订单编号
- `market` — 交易市场
- `order_sysid` — 柜台合同编号
- `error_id` — 错误代码
- `error_msg` — 错误信息

## 回调类 XtQuantTraderCallback

```python
class MyXtQuantTraderCallback(XtQuantTraderCallback):
    def on_disconnected(self):
        """连接断开"""

    def on_account_status(self, status):  # XtAccountStatus
        """账号状态变动"""

    def on_stock_asset(self, asset):  # XtAsset
        """资金变动"""

    def on_stock_order(self, order):  # XtOrder
        """委托变动"""

    def on_stock_trade(self, trade):  # XtTrade
        """成交变动"""

    def on_stock_position(self, position):  # XtPosition
        """持仓变动"""

    def on_order_error(self, order_error):  # XtOrderError
        """下单失败"""

    def on_cancel_error(self, cancel_error):  # XtCancelError
        """撤单失败"""

    def on_order_stock_async_response(self, response):  # XtOrderResponse
        """异步下单回报"""

    def on_smt_appointment_async_response(self, response):  # XtSmtAppointmentResponse
        """约券异步回报"""
```
