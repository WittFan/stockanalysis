# XtQuant.XtData 行情模块 API 参考

## 概述

xtdata 是 xtquant 库中提供行情相关数据的模块，通过与 MiniQmt 客户端建立连接获取数据。

接口分为三类：
- `subscribe_` - 订阅行情推送
- `get_` - 从缓存/本地获取数据
- `download_` - 补充下载历史数据到本地

## 常用类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `stock_code` | 合约代码，格式 `code.market` | `000001.SZ`, `600000.SH` |
| `period` | K线周期 | `tick`, `1m`, `5m`, `15m`, `30m`, `1h`, `1d` |
| `dividend_type` | 复权方式 | `none`(不复权), `front`(前复权), `back`(后复权), `front_ratio`(等比前复权), `back_ratio`(等比后复权) |
| 时间范围 | `[start_time, end_time]` 闭区间 | `'20230101'`, `'20231231093000'` |
| `count` | 数据条数，与时间范围配合使用 | `-1` 表示不限制 |

## 行情接口

### subscribe_quote - 订阅单股行情

```python
subscribe_quote(stock_code, period='1d', start_time='', end_time='', count=0, callback=None)
```

- `callback`: `on_data(datas)`，datas 格式 `{stock_code: [data1, data2, ...]}`
- 返回：订阅号（int），`>0` 成功，`-1` 失败

### subscribe_whole_quote - 订阅全推行情

```python
subscribe_whole_quote(code_list, callback=None)
```

- `code_list`: 市场代码 `['SH', 'SZ']` 或合约代码 `['600000.SH']`
- `callback`: `on_data(datas)`，datas 格式 `{stock1: data1, stock2: data2}`
- 全推适合大量订阅场景，单股订阅建议不超过 50 个

### unsubscribe_quote - 反订阅

```python
unsubscribe_quote(seq)
```

- `seq`: subscribe_quote 返回的订阅号

### run - 阻塞接收回调

```python
run()
```

阻塞当前线程，持续接收行情回调推送。

### get_market_data - 获取行情数据（主要接口）

```python
get_market_data(field_list=[], stock_list=[], period='1d', start_time='', end_time='', count=-1, dividend_type='none', fill_data=True)
```

- `field_list`: 需要的字段列表，空列表返回全部字段
- `fill_data`: 是否向前填充停牌数据
- 返回 K线：`dict {field: DataFrame(index=stock_list, columns=time_list)}`
- 返回 tick：`dict {stock: ndarray}`

### get_local_data - 从本地文件获取行情

```python
get_local_data(field_list=[], stock_code=[], period='1d', start_time='', end_time='', count=-1, dividend_type='none', fill_data=True, data_dir=data_dir)
```

- `data_dir`: MiniQmt 的 `userdata_mini` 路径
- 其余参数同 `get_market_data`

### get_full_tick - 获取全推数据

```python
get_full_tick(code_list)
```

- 返回：`dict {stock1: data1, stock2: data2}`

### get_divid_factors - 获取除权数据

```python
get_divid_factors(stock_code, start_time='', end_time='')
```

- 返回：`pd.DataFrame`

### get_l2_quote - Level2 行情快照

```python
get_l2_quote(field_list=[], stock_code='', start_time='', end_time='', count=-1)
```

- 返回：`np.ndarray`

### get_l2_order / get_l2_transaction

参数结构同 `get_l2_quote`，分别获取 Level2 逐笔委托和逐笔成交数据。

### download_history_data - 补充历史行情（同步）

```python
download_history_data(stock_code, period, start_time='', end_time='', incrementally=None)
```

- `incrementally`: 是否增量下载
- 同步执行，适合单只合约

### download_history_data2 - 批量补充历史行情

```python
download_history_data2(stock_list, period, start_time='', end_time='', callback=None)
```

- `callback`: 进度回调，参数格式 `{finished, total, stockcode, message}`

## 交易日历接口

```python
get_holidays()
```
返回节假日列表。

```python
get_trading_calendar(market, start_time='', end_time='', tradetimes=False)
```
返回交易日历，`tradetimes=True` 时附带交易时段信息。

```python
get_trading_dates(market, start_time='', end_time='', count=-1)
```
返回交易日列表。

```python
get_trade_times(stockcode)
```
返回合约交易时段。

## 基础行情信息

### get_instrument_detail - 合约基础信息

```python
get_instrument_detail(stock_code)
```

返回字段包括：
- `ExchangeID` - 交易所代码
- `InstrumentName` - 合约名称
- `PreClose` - 昨收价
- `UpStopPrice` / `DownStopPrice` - 涨停价/跌停价
- `FloatVolume` - 流通股本
- `TotalVolume` - 总股本
- `PriceTick` - 最小价格变动

### get_instrument_type - 合约类型

```python
get_instrument_type(stock_code)
```

返回类型：`index`(指数), `stock`(股票), `fund`(基金), `etf`

## 板块接口

### 查询

```python
get_sector_list()                          # 板块列表
get_stock_list_in_sector(sector_name)      # 板块成分股
get_index_weight(index_code)               # 指数成分权重
```

### 下载

```python
download_sector_data()                     # 下载板块分类数据
download_index_weight()                    # 下载指数成分权重数据
```

### 自定义板块管理

```python
create_sector_folder(folder_name)          # 创建板块目录
create_sector(sector_name, stock_list)     # 创建自定义板块
add_sector(sector_name, stock_list)        # 添加成分股
remove_stock_from_sector(sector_name, stock_list)  # 移除成分股
remove_sector(sector_name)                 # 删除板块
reset_sector(sector_name, stock_list)      # 重置板块成分
```

## 财务数据接口

### get_financial_data - 获取财务数据

```python
get_financial_data(stock_list, table_list=[], start_time='', end_time='', report_type='report_time')
```

- `table_list` 可选值：
  - `Balance` - 资产负债表
  - `Income` - 利润表
  - `CashFlow` - 现金流量表
  - `Capital` - 股本结构
  - `Holdernum` - 股东人数
  - `Top10holder` - 十大股东
  - `Top10flowholder` - 十大流通股东
  - `Pershareindex` - 每股指标
- `report_type`: `'report_time'`(报告期) 或 `'announce_time'`(公告期)

### download_financial_data - 下载财务数据

```python
download_financial_data(stock_list, table_list=[])
download_financial_data2(stock_list, table_list=[], start_time='', end_time='', callback=None)
```

`download_financial_data2` 支持进度回调。

## 其他接口

```python
download_cb_data()                         # 下载可转债信息
get_cb_info(stockcode)                     # 获取可转债详情
get_ipo_info(start_time, end_time)         # 新股申购信息
get_period_list()                          # 可用K线周期列表
reconnect()                                # 重新连接到指定ip端口
```

## 附录：行情数据字段

### tick 分笔数据字段

| 字段 | 说明 |
|------|------|
| `time` | 时间戳 |
| `lastPrice` | 最新价 |
| `open` / `high` / `low` | 开盘/最高/最低 |
| `lastClose` | 昨收价 |
| `amount` | 成交额 |
| `volume` | 成交量（股） |
| `pvolume` | 成交量（手） |
| `stockStatus` | 合约状态 |
| `openInt` | 持仓量 |
| `lastSettlementPrice` | 昨结算价 |
| `askPrice` / `bidPrice` | 卖价/买价（5档） |
| `askVol` / `bidVol` | 卖量/买量（5档） |

### K线数据字段（1m/5m/1d 等）

| 字段 | 说明 |
|------|------|
| `time` | 时间戳 |
| `open` / `high` / `low` / `close` | 开高低收 |
| `volume` | 成交量 |
| `amount` | 成交额 |
| `settelementPrice` | 结算价 |
| `openInterest` | 持仓量 |
| `preClose` | 昨收价 |
| `suspendFlag` | 停牌标记：`0` 正常，`1` 停牌，`-1` 复牌 |

### 除权数据字段

| 字段 | 说明 |
|------|------|
| `interest` | 每股派息 |
| `stockBonus` | 每股送股 |
| `stockGift` | 每股转增 |
| `allotNum` | 每股配股数 |
| `allotPrice` | 配股价 |
| `gugai` | 股改 |
| `dr` | 除权标记 |

## 请求限制

- 全推数据（`subscribe_whole_quote`）适合大量订阅场景
- 单股订阅（`subscribe_quote`）建议不超过 50 个
- 板块分类信息按周/日更新即可，无需频繁下载
