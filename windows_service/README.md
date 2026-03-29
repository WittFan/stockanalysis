# QMT REST API 服务（Windows 端）

将 xtdata（行情）和 xttrader（交易/查询）的全部接口暴露为 HTTP API，供 Mac 端或其他客户端调用。

> **功能边界**：本服务仅负责 QMT 交易接口代理，不涉及回测逻辑。回测、因子计算、策略逻辑全部在 Mac 端实现。

---

## 目录结构

```
windows_service/
├── config.py               # 配置（QMT路径、账号、API端口）
├── qmt_connection.py       # QMT 连接封装（直接调用 xtquant，不依赖 Backtrader）
├── api_server.py           # REST API 服务（xtdata + xttrader 全部接口）
├── run_service.py          # 启动脚本
├── check_env.py            # Windows 环境检查
├── mac_client_example.py   # Mac 端调用示例（QMTClient 类）
├── xtquant/                # xtquant 本地副本（从 MiniQMT 安装目录复制）
└── README.md               # 本文件
```

---

## 快速开始

### 1. 准备 xtquant

xtquant 是 MiniQMT 自带的 Python 库，有两种方式使用：

**方式一（推荐）：复制到本地目录**
```cmd
xcopy /E "C:\国金QMT交易端\bin.x64\Lib\site-packages\xtquant" .\xtquant\
```

**方式二：添加到 PYTHONPATH**
```cmd
set PYTHONPATH=C:\国金QMT交易端\bin.x64\Lib\site-packages
```

### 2. 安装依赖

```cmd
pip install flask flask-cors loguru requests
```

### 3. 修改配置

编辑 `config.py`：

```python
QMT_PATH    = r'C:\国金QMT交易端模拟\userdata_mini'  # MiniQMT userdata_mini 路径
QMT_ACCOUNT = ''                              # 资金账号
QMT_SESSION = 123456                                  # 会话ID（多策略时各取不同值）
API_PORT    = 8080                                    # 监听端口
API_TOKEN   = ''                                      # 认证Token（空表示不启用）
```

或通过环境变量覆盖（优先级更高）：

```cmd
set QMT_PATH=C:\国金QMT交易端模拟\userdata_mini
set QMT_ACCOUNT=55003046
set API_PORT=8080
set API_TOKEN=your-secret-token
```

### 4. 检查环境

```cmd
python check_env.py
```

### 5. 启动 MiniQMT，然后启动服务

```cmd
python run_service.py
```

其他选项：

```cmd
python run_service.py --api-port 8080    # 指定端口
python run_service.py --dry-run          # 不连接QMT，仅测试API路由
```

服务启动后访问：`http://<Windows_IP>:8080/`

---

## REST API 接口

所有接口均需在 HTTP Header 中携带 `X-API-Token`（若 `config.API_TOKEN` 非空）。

### 基础

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查（无需认证） |
| GET | `/api/status` | 连接状态与基础配置 |

```bash
# 健康检查
curl http://10.211.55.16:8080/health
# → {"status": "healthy", "connected": true}

# 连接状态
curl http://10.211.55.16:8080/api/status
# → {"connected": true, "account_id": "55003046", "timestamp": "..."}
```

---

### xttrader — 账户查询

| 方法 | 路径 | 说明 | 对应接口 |
|------|------|------|---------|
| GET | `/api/query/asset` | 账户资产 | `query_stock_asset` |
| GET | `/api/query/positions` | 持仓列表 | `query_stock_positions` |
| GET | `/api/query/orders` | 当日委托 | `query_stock_orders` |
| GET | `/api/query/trades` | 当日成交 | `query_stock_trades` |

```bash
curl http://10.211.55.16:8080/api/query/asset
curl "http://10.211.55.16:8080/api/query/orders?cancelable_only=true"
```

**持仓字段：** `stock_code`, `volume`, `can_use_volume`, `frozen_volume`, `avg_price`, `open_price`, `market_value`, `on_road_volume`, `yesterday_volume`

**委托字段：** `order_id`, `order_sysid`, `stock_code`, `order_type`, `order_volume`, `price_type`, `price`, `traded_volume`, `traded_price`, `order_status`, `status_msg`, `strategy_name`

**成交字段：** `stock_code`, `traded_id`, `traded_time`, `traded_price`, `traded_volume`, `traded_amount`, `order_id`, `strategy_name`

---

### xttrader — 下单 / 撤单

| 方法 | 路径 | 说明 | 对应接口 |
|------|------|------|---------|
| POST | `/api/trade/order` | 同步下单 | `order_stock` |
| POST | `/api/trade/order_async` | 异步下单 | `order_stock_async` |
| POST | `/api/trade/cancel` | 撤单（按order_id） | `cancel_order_stock` |
| POST | `/api/trade/cancel_sysid` | 撤单（按柜台合同号） | `cancel_order_stock_sysid` |

**下单 Body：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `stock_code` | str | 必填，如 `511220.SH` |
| `order_type` | str | `buy` \| `sell` |
| `order_volume` | int | 委托数量（股，A股最小 100 股） |
| `price_type` | str | `latest`（最新价）\| `fix`（指定价），默认 `latest` |
| `price` | float | `price_type=fix` 时必填 |
| `strategy_name` | str | 由 Mac 策略端传入（对应 `ProjConfig.name`），写入 QMT 委托记录 |
| `order_remark` | str | 可选，委托备注 |

```bash
# 同步下单
curl -X POST http://10.211.55.16:8080/api/trade/order \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code":    "511220.SH",
    "order_type":    "buy",
    "order_volume":  1000,
    "price_type":    "latest",
    "strategy_name": "etf_rp"
  }'

# 撤单
curl -X POST http://10.211.55.16:8080/api/trade/cancel \
  -H "Content-Type: application/json" \
  -d '{"order_id": 12345}'
```

---

### 回调事件（推送消费）

MiniQMT 通过回调主动推送委托/成交/错误事件，Windows 服务将其缓冲到队列，Mac 端通过以下接口**轮询消费**（每次调用后事件即出队，不可重复消费）。

| 方法 | 路径 | 说明 | 对应回调 |
|------|------|------|---------|
| GET | `/api/events/orders` | 委托状态变更 | `on_stock_order` |
| GET | `/api/events/trades` | 成交回报 | `on_stock_trade` |
| GET | `/api/events/errors` | 下单/撤单错误 | `on_order_error` / `on_cancel_error` |
| GET | `/api/events/async_responses` | 异步下单/撤单响应 | `on_order_stock_async_response` |

所有接口支持 `?limit=N` 参数（默认 50），一次最多取 N 条。

```bash
# 消费委托推送（报单/撤单/成交/拒绝）
curl http://10.211.55.16:8080/api/events/orders
# → [{"order_id":12345,"stock_code":"511220.SH","order_status":50,"status_msg":"已成交",...}]

# 消费成交回报
curl http://10.211.55.16:8080/api/events/trades
# → [{"stock_code":"511220.SH","traded_volume":1000,"traded_price":10.28,...}]

# 消费错误事件
curl http://10.211.55.16:8080/api/events/errors
# → [{"type":"order_error","order_id":12345,"error_id":50,"error_msg":"资金不足"}]

# 消费异步下单响应（seq → order_id 映射）
curl http://10.211.55.16:8080/api/events/async_responses
# → [{"type":"order_async","seq":1,"order_id":12345,"error_id":0}]
```

> **建议**：Mac 端策略在交易时段内每 2-5 秒轮询一次 `/api/events/orders` 和 `/api/events/trades`，以感知委托状态变化。

---

### xtdata — 行情数据

| 方法 | 路径 | 说明 | 对应接口 |
|------|------|------|---------|
| GET | `/api/market/kline` | K线历史数据 | `get_market_data` |
| GET | `/api/market/tick` | Tick 快照 | `get_full_tick` |
| GET | `/api/market/instrument` | 合约基础信息 | `get_instrument_detail` |
| GET | `/api/market/instrument_type` | 合约类型 | `get_instrument_type` |
| GET | `/api/market/calendar` | 交易日历 | `get_trading_dates` |
| GET | `/api/market/holidays` | 节假日列表 | `get_holidays` |
| GET | `/api/market/sector` | 板块列表 | `get_sector_list` |
| GET | `/api/market/sector/<板块名>` | 板块成分股 | `get_stock_list_in_sector` |
| GET | `/api/market/index_weight` | 指数成分权重 | `get_index_weight` |
| GET | `/api/market/divid` | 除权数据 | `get_divid_factors` |
| GET | `/api/market/financial` | 财务数据 | `get_financial_data` |
| GET | `/api/market/ipo` | 新股申购信息 | `get_ipo_info` |

**K线数据参数：**

| 参数 | 说明 | 默认 |
|------|------|------|
| `stocks` | 逗号分隔的合约代码（必填） | — |
| `period` | `tick`/`1m`/`5m`/`15m`/`30m`/`1h`/`1d` | `1d` |
| `start` | 开始日期，如 `20240101` | — |
| `end` | 结束日期 | — |
| `fields` | 逗号分隔字段，空则返回全部 | — |
| `dividend_type` | `none`/`front`/`back`/`front_ratio`/`back_ratio` | `none` |
| `count` | 数据条数，`-1` 不限 | `-1` |

响应格式：`{stock_code: {field: [values...]}}`

```bash
# K线（前复权日K）
curl "http://10.211.55.16:8080/api/market/kline?stocks=511220.SH,159915.SZ&period=1d&start=20240101&end=20241231&dividend_type=front"

# Tick 快照
curl "http://10.211.55.16:8080/api/market/tick?stocks=511220.SH"

# 合约信息
curl "http://10.211.55.16:8080/api/market/instrument?stock=511220.SH"

# 交易日历
curl "http://10.211.55.16:8080/api/market/calendar?market=SH&start=20240101&end=20241231"

# 板块成分股
curl "http://10.211.55.16:8080/api/market/sector/沪深300"

# 指数权重
curl "http://10.211.55.16:8080/api/market/index_weight?index=000300.SH"

# 财务数据（tables: Balance/Income/CashFlow/Capital/Pershareindex）
curl "http://10.211.55.16:8080/api/market/financial?stocks=600000.SH&tables=Income,Balance&start=20230101&end=20231231"
```

---

## Mac 端调用

### 方式一：使用封装好的 QMTClient

```python
from mac_client_example import QMTClient

client = QMTClient(host='10.211.55.16', port=8080, token='')

# 查询账户资产
asset = client.query_asset()

# 下单（strategy_name 由 Mac 策略端的 ProjConfig.name 传入）
result = client.order('511220.SH', 'buy', 1000, strategy_name='etf_rp')

# K线数据
kline = client.kline(['511220.SH'], period='1d', start='20240101', end='20241231')

# 板块成分股
stocks = client.sector_stocks('沪深300')
```

运行交互式演示：
```bash
python mac_client_example.py
```

### 方式二：直接 curl

```bash
# 健康检查
curl http://10.211.55.16:8080/health

# 查持仓（带 Token 认证时加 Header）
curl -H "X-API-Token: your-token" http://10.211.55.16:8080/api/query/positions

# 下单
curl -X POST http://10.211.55.16:8080/api/trade/order \
  -H "X-API-Token: your-token" \
  -H "Content-Type: application/json" \
  -d '{"stock_code":"511220.SH","order_type":"buy","order_volume":1000,"strategy_name":"etf_rp"}'
```

---

## 防火墙配置（Windows）

允许外部访问 API 端口（管理员运行）：

```cmd
netsh advfirewall firewall add rule name="QMT API" dir=in action=allow protocol=tcp localport=8080
```

---

## 常见问题

**Q: QMT 连接失败**
- 确认 MiniQMT 客户端已启动并登录
- 检查 `config.py` 中 `QMT_PATH` 是否为正确的 `userdata_mini` 路径
- 先运行 `python check_env.py` 排查环境问题

**Q: xtquant 找不到**
- 将 MiniQMT 安装目录下的 `xtquant` 文件夹复制到 `windows_service/` 目录下
- 或将 xtquant 所在目录添加到 `PYTHONPATH` 环境变量

**Q: Mac 无法访问 API**
- 确认 Windows 防火墙已放行端口（见上方防火墙配置）
- `config.py` 中 `API_HOST` 必须设为 `0.0.0.0`
- 用 `ipconfig` 确认 Windows IP 地址

**Q: 行情数据为空**
- 非交易时段 `get_full_tick` 可能返回空数据，属正常现象
- K线历史数据需先通过 MiniQMT 客户端下载到本地

**Q: 下单失败**
- 检查 `order_volume` 是否为 100 的整数倍（A股最小交易单位 100 股）
- 查看 Windows 端日志 `logs/qmt_api_YYYYMMDD.log`

**Q: 什么时间可以实时交易？**

A 股交易时段（非交易时段下单会被拒绝）：

| 时段 | 时间 |
|------|------|
| 集合竞价（可撤单） | 09:15 - 09:20 |
| 集合竞价（锁定） | 09:20 - 09:25 |
| 上午开盘 | 09:30 - 11:30 |
| 下午开盘 | 13:00 - 15:00 |
| 收盘集合竞价（深市）| 14:57 - 15:00 |

周末及法定节假日休市。**Mac 端策略在触发下单前应先校验当前时间是否在交易时段内。**
