# StockAnalysis 量化投研平台 - 开发文档

## 一、项目概述

AI智能量化投研平台，用于股票/基金/指数数据管理、因子计算、策略回测与绩效分析。

**技术栈：**
- 数据库：DuckDB（SQLAlchemy ORM）
- 数据源：Tushare API
- 回测+实盘引擎：Backtrader（统一）+ 自定义算子系统
- 实盘对接：QMT (xtquant) via Windows REST API 服务
- GUI：wxPython
- 数据处理：Pandas、NumPy、TA-Lib
- 机器学习：AutoGluon、LightGBM
- 可视化：Bokeh
- 日志：Loguru
- 日期处理：Pendulum

---

## 二、项目架构

### 整体架构图

本项目采用 **Mac 主端 + Windows 交易服务** 的跨平台架构：

- **Mac 端**：承载全部研究、开发、回测、数据管理工作
- **Windows 端**：仅运行 QMT 交易接口代理服务，功能严格隔离

```
╔══════════════════════════════════════════════════════════════╗
║                    Mac 端（主环境）                           ║
║                                                              ║
║  ┌─────────────────────────────────────────────────────┐    ║
║  │                   GUI (wxPython)                     │    ║
║  │                    main.py                           │    ║
║  ├─────────────────────────────────────────────────────┤    ║
║  │              回测引擎 (engine/)                       │    ║
║  │  ┌──────────┐ ┌──────────┐ ┌───────────────────┐    │    ║
║  │  │Engine   │ │ Strategy │ │ Performance       │    │    ║
║  │  │ 回测控制 │ │ 策略执行  │ │ 绩效分析          │    │    ║
║  │  └────┬─────┘ └────┬─────┘ └───────────────────┘    │    ║
║  │       │            │                                 │    ║
║  │  ┌────▼────────────▼──────────────────────────┐     │    ║
║  │  │          algos/ 算子系统                     │     │    ║
║  │  │  时间控制 │ 选股 │ 权重 │ 再平衡 │ 择时     │     │    ║
║  │  └────────────────────────────────────────────┘     │    ║
║  ├─────────────────────────────────────────────────────┤    ║
║  │            数据加载层 (datafeed/)                     │    ║
║  │  ┌──────────────┐  ┌──────────────────────────┐     │    ║
║  │  │ Duckdbloader │  │ expr 表达式/因子计算引擎   │     │    ║
║  │  └──────┬───────┘  └──────────────────────────┘     │    ║
║  ├─────────┼───────────────────────────────────────────┤    ║
║  │         │      ORM 模型层 (orm_models/)              │    ║
║  │  ┌──────▼───────┐  ┌──────────────────────────┐     │    ║
║  │  │   DataApi    │  │  table_models/ 数据表定义  │     │    ║
║  │  │  数据库CRUD  │  │  股票/基金/指数/交易日历    │     │    ║
║  │  └──────┬───────┘  └──────────────────────────┘     │    ║
║  ├─────────┼───────────────────────────────────────────┤    ║
║  │         │      数据拉取层 (pull_tushare/)             │    ║
║  │  ┌──────▼───────┐  ┌──────────────────────────┐     │    ║
║  │  │  主控程序    │  │ tushare_tables/ 各表拉取   │     │    ║
║  │  │  多线程调度  │  │ 元数据 / 明细数据 基类     │     │    ║
║  │  └──────┬───────┘  └──────────────────────────┘     │    ║
║  ├─────────┼───────────────────────────────────────────┤    ║
║  │         ▼                                            │    ║
║  │   ┌─────────────┐    ┌────────────┐                  │    ║
║  │   │ Tushare API │    │  DuckDB    │                  │    ║
║  │   └─────────────┘    │ data/duck.db│                 │    ║
║  │                      └────────────┘                  │    ║
║  └─────────────────────────────────────────────────────┘    ║
║                           │ HTTP REST API                    ║
╚═══════════════════════════╪══════════════════════════════════╝
                            │
╔═══════════════════════════╪══════════════════════════════════╗
║                Windows 端 ↓（交易服务专用）                   ║
║                                                              ║
║  ┌─────────────────────────────────────────────────────┐    ║
║  │         windows_service/ — QMT REST API 服务         │    ║
║  │   api_server.py（Flask）+ run_service.py             │    ║
║  ├──────────────────────┬──────────────────────────────┤    ║
║  │   xttrader 交易接口   │      xtdata 行情接口          │    ║
║  │  下单 / 撤单 / 查询   │  K线 / Tick / 合约信息等      │    ║
║  └──────────┬───────────┴─────────────┬────────────────┘    ║
║             │                         │                      ║
║             └──────────┬──────────────┘                      ║
║                   ┌────▼──────┐                              ║
║                   │  MiniQMT  │  ← xttrader + xtdata        ║
║                   │  交易终端  │    均通过 MiniQMT 连接        ║
║                   └───────────┘                              ║
╚══════════════════════════════════════════════════════════════╝
```

### 数据流向

**模式一：回测模式（Mac 本地）**

```
Tushare API → pull_tushare(多线程) → ORM Models → DuckDB
                                                    ↓
                                          datafeed.Duckdbloader
                                                    ↓
                                          expr(因子计算)
                                                    ↓
                                          engine.StrategyAlgos（Backtrader Cerebro）
                                                    ↓
                                          algos(算子链：选股→权重→再平衡)
                                                    ↓
                                          performance(绩效分析) → Bokeh(可视化)
```

**模式二：实时交易模式（Mac 策略端 + Windows 交易端）**

```
【Mac 端】
  DuckDB / xtdata(历史K线) → datafeed → expr(因子计算)
                                              ↓
                                   engine.StrategyAlgos（实盘信号生成）
                                              ↓
                                   algos(算子链：选股→权重→目标仓位)
                                              ↓
                                   QMTClient（HTTP 请求）
                                              │
                        ┌─────────────────────┘
                        ↓ HTTP REST API
【Windows 端】
  windows_service/api_server.py
          ├── /api/trade/order  → xttrader.order_stock()  → MiniQMT → 交易所
          ├── /api/query/*      → xttrader.query_*()      → MiniQMT（持仓/委托/成交回查）
          └── /api/market/*     → xtdata.get_market_data()→ MiniQMT（实时行情）
```

---

## 三、目录结构

```
stockanalysis/
├── config.py                    # 全局配置（DB_URI、tushare_token、路径）
├── config_default.py            # 默认配置模板
├── main.py                      # GUI 主程序入口
│
├── orm_models/                  # 数据库 ORM 模型层
│   ├── api.py                   # DataApi 数据库操作接口
│   ├── base.py                  # SQLAlchemy Base 基类
│   ├── register.py              # 数据库初始化（建表）
│   └── table_models/            # 数据表模型定义
│       ├── exchange_info.py     # 交易日历（TradeCal）
│       ├── stock_info.py        # 股票基本信息（StockBasic）
│       ├── stock_trade.py       # 股票日线行情（Daily、Weekly、Monthly）
│       ├── fund.py              # 基金（FundBasic、FundNav、FundDaily）
│       ├── index.py             # 指数（IndexBasic、IndexDaily、IndexMember）
│       ├── foreign_currency.py  # 外汇
│       ├── reports.py           # 财报
│       └── update_info.py       # 数据更新记录
│
├── pull_tushare/                # 数据拉取层
│   ├── main.py                  # 拉取主控程序（多线程调度）
│   ├── TushareApi.py            # Tushare API 封装
│   └── tushare_tables/          # 各数据表拉取实现
│       ├── meta_data_base.py    # 元数据下载基类
│       ├── detail_data_base.py  # 明细数据下载基类（支持增量更新）
│       ├── daily_tushare.py     # 股票日线
│       ├── index_daily_tushare.py  # 指数日线
│       ├── fund_daily_tushare.py   # 基金日线
│       ├── fund_nav_tushare.py     # 基金净值
│       └── adj_factor_tushare.py   # 复权因子
│
├── datafeed/                    # 数据加载与因子计算
│   ├── dataloader.py            # Duckdbloader 数据库→回测数据
│   ├── expr.py                  # 表达式计算引擎
│   ├── expr_funcs.py            # 内置函数（shift、rolling 等）
│   ├── expr_funcs_pair.py       # 配对因子函数
│   ├── expr_funcs_talib.py      # TA-Lib 技术指标封装
│   ├── expr_rolling.py          # 滚动窗口函数
│   ├── bt_datafeed.py           # Backtrader 数据源适配
│   └── factor/
│       └── alpha.py             # Alpha 因子
│
├── engine/                      # 回测引擎
│   ├── engine.py                # Engine + StrategyAlgos 核心类
│   ├── proj_config.py           # ProjConfig / AlgoConfig 策略配置
│   ├── engine_utils.py          # 数据加载工具
│   ├── strategy.py              # StrategyBase 策略基类
│   ├── performance.py           # 绩效指标（CAGR、Sharpe、MaxDD 等）
│   ├── results.py               # 回测结果处理
│   ├── show_results.py          # Bokeh 绘图展示
│   ├── ffn_performance.py       # FFN 库集成
│   ├── utils.py                 # 工具函数
│   ├── algos/                   # 策略算子
│   │   ├── algo_base.py         # Algo / AlgoStack 基类
│   │   ├── algos_date.py        # 时间控制（RunOnce、RunWeekly 等）
│   │   ├── algos_select.py      # 选股（SelectAll、SelectBySignal）
│   │   ├── algos_weight.py      # 权重（WeightEqually、WeightERC）
│   │   ├── algos_balance.py     # 再平衡（Rebalance）
│   │   ├── algos_grid.py        # 网格交易
│   │   ├── algos_model.py       # 机器学习选股
│   │   ├── algos_turtle.py      # 海龟交易
│   │   ├── algos_picktime.py    # 择时
│   │   └── algos_debug.py       # 调试输出
│   ├── models/                  # 机器学习模型
│   │   ├── model_base.py        # 模型基类
│   │   ├── gbdt_lgb.py          # LightGBM
│   │   └── stock_ranker.py      # 股票排名
│   └── pyrb/                    # 风险平价优化
│       ├── allocation.py        # 资产配置
│       ├── solvers.py           # 求解器
│       └── validation.py        # 验证
│
├── gui/                         # GUI 界面（wxPython）
│   ├── mainframe.py             # 主窗口
│   ├── global_events.py         # 事件处理
│   ├── proj_loader.py           # 项目加载
│   ├── panels/                  # 面板
│   └── widgets/                 # 控件
│
├── utils/                       # 公共工具
│   ├── logger.py                # Loguru 日志
│   └── datetime_transformer.py  # Pendulum 日期转换
│
├── alphagen/                    # 强化学习 Alpha 因子生成（独立模块）
├── xtquant/                     # 迅投 QMT 量化交易接口（Windows 端依赖）
├── notebook/                    # Jupyter 分析笔记
│
├── windows_service/             # ⚠️ Windows 端部署（仅 QMT 交易接口服务）
│   ├── config.py                # 配置（QMT路径、账号、API端口）
│   ├── api_server.py            # REST API 服务（xtdata + xttrader 全部接口）
│   ├── run_service.py           # 启动脚本
│   ├── check_env.py             # Windows 环境检查
│   ├── mac_client_example.py   # Mac 端调用示例（QMTClient 类）
│   └── README.md                # 部署说明
│
├── data/                        # 数据目录
│   ├── duck.db                  # DuckDB 数据库文件
│   ├── csvs/                    # CSV 数据（futures/bonds/etfs/index）
│   └── projs/                   # 策略项目配置（TOML 格式）
│
└── logs/                        # 运行日志
```

---

## 四、核心模块详解

### 4.1 配置 (config.py)

```python
DB_URI = "duckdb:///data/duck.db"   # 数据库连接
tushare_token = "your_token"        # Tushare API Token
cpu_count = 4                       # 多线程核心数
WORKDIR = "/path/to/project"
DATA_DIR = WORKDIR + "/data"
```

配置模板见 `config_default.py`，首次使用需复制为 `config.py` 并填入 Tushare Token。

### 4.2 ORM 数据层 (orm_models/)

**DataApi (api.py)** 是数据库操作的统一接口：

| 方法 | 功能 |
|------|------|
| `write(df, table_class)` | 将 DataFrame 写入数据库 |
| `delete_data(table, filters)` | 按条件删除 |
| `query(table, filters)` | 查询返回 DataFrame |
| `read(table, symbols, start, end)` | 按标的和时间范围查询 |
| `read_symbols(table, symbols)` | 按标的代码批量查询 |
| `basic_info(table)` | 获取基本信息表 |
| `get_SSE_cal(start, end)` | 获取交易日历 |

**数据表模型** 使用 SQLAlchemy 声明式定义，均继承自 `base.py` 的 Base。主要表：

- `TradeCal` - 交易日历
- `StockBasic` - 股票列表
- `Daily` / `Weekly` / `Monthly` - 股票行情
- `IndexBasic` / `IndexDaily` - 指数数据
- `FundBasic` / `FundNav` / `FundDaily` - 基金数据
- `UpdateInfo` - 数据更新记录（用于增量更新）

### 4.3 数据拉取 (pull_tushare/)

**两种基类：**

1. **MetaDataBase** - 元数据（低频更新）
   - 股票/指数/基金基本信息
   - 更新频率：yearly / monthly

2. **DetailDataBase** - 明细数据（高频更新）
   - 日线行情、净值、复权因子
   - 支持增量更新（记录 `update_info` 表）
   - 自动去重

**拉取主控 (main.py)** 使用 `ThreadPoolExecutor` 多线程调度，受 Tushare API 频率限制控制。

### 4.4 数据加载 (datafeed/)

**Duckdbloader (dataloader.py)** 负责：
- 从 DuckDB 加载指定标的和时间范围的数据
- 转换为 PyBroker 所需的 DataFrame 格式
- 支持动态因子计算

**表达式引擎 (expr.py)** 支持字符串表达式计算因子：
```python
# 示例：5日收益率
calc_expr(df, "close/shift(close,5)-1")

# 支持的函数
shift(series, n)          # 滞后
rolling_mean(series, n)   # 滚动均值
rolling_std(series, n)    # 滚动标准差
# TA-Lib 指标
ta_sma(series, n)         # 简单移动平均
ta_ema(series, n)         # 指数移动平均
ta_rsi(series, n)         # RSI
```

### 4.5 回测引擎 (engine/)

#### Engine 类 (engine.py)

```python
class Engine:
    def __init__(self, proj_config: ProjConfig):
        # 初始化策略、加载数据
    def run(self):
        # 执行回测
    def analysis(self, console=True):
        # 输出绩效报告和图表
```

#### StrategyAlgos (engine.py)

继承 PyBroker 的 Strategy，每个 bar 依次执行算子链：

```python
class StrategyAlgos(Strategy):
    def on_bar(self, dt):
        for algo in self.algos:
            if not algo(target):
                return  # 某算子返回 False 则停止
```

#### 策略配置 (proj_config.py)

```python
@dataclass
class ProjConfig:
    name: str                    # 策略名称
    start_date: str              # 回测开始日期
    end_date: str                # 回测结束日期
    commission: float = 0.001    # 手续费率
    slippage: float = 0.001      # 滑点
    symbols: list[str]           # 标的列表
    benchmark: str               # 基准标的
    algos: list[AlgoConfig]      # 算子配置列表
    data_folder: str             # 数据源文件夹
    fields: list[str]            # 因子字段
    names: list[str]             # 因子名称
```

### 4.6 算子系统 (engine/algos/)

**设计理念：** 每个 Algo 执行一个独立任务，返回 `True`（继续）或 `False`（停止），通过 AlgoStack 串联组合。

| 类别 | 算子 | 功能 |
|------|------|------|
| 时间控制 | `RunOnce` | 仅首次执行 |
| | `RunWeekly` | 每周执行 |
| | `RunMonthly` | 每月执行 |
| | `RunPeriod(n)` | 每 n 天执行 |
| 选股 | `SelectAll` | 选择全部标的 |
| | `SelectBySignal` | 按信号选股 |
| 权重 | `WeightEqually` | 等权重 |
| | `WeightERC` | 风险平价（ERC） |
| 再平衡 | `Rebalance` | 执行调仓 |
| 网格 | `GridTrade` | 网格交易 |
| 择时 | `PickTime` | 择时信号 |
| 调试 | `PrintDate` | 打印当前日期 |
| | `PrintTempData` | 打印临时数据 |

**自定义算子：**
```python
from engine.algos.algo_base import Algo

class MyAlgo(Algo):
    def __call__(self, target):
        # target.now      当前日期
        # target.universe 当前标的池
        # target.temp     临时数据字典
        # 实现逻辑...
        return True  # 返回 True 继续执行后续算子
```

### 4.7 绩效分析 (engine/performance.py)

计算指标：

| 指标 | 说明 |
|------|------|
| CAGR | 年化复合收益率 |
| Volatility | 年化波动率 |
| Sharpe Ratio | 夏普比率 |
| Max Drawdown | 最大回撤 |
| Calmar Ratio | 卡尔玛比率（CAGR / MaxDD） |
| Win Rate | 胜率 |

---

## 五、跨平台部署架构

### 5.1 职责划分原则

本项目严格按"功能归属"划分运行环境，**Windows 端仅作为 QMT 交易接口的代理层**，不承载任何业务逻辑：

| 功能 | 运行端 | 说明 |
|------|--------|------|
| 策略研究 / 因子计算 | Mac | datafeed/expr 表达式引擎 |
| 历史数据管理 | Mac | pull_tushare + DuckDB |
| **策略回测** | **Mac** | **Backtrader 回测引擎，不在 Windows 运行** |
| 绩效分析 / 可视化 | Mac | engine/performance + Bokeh |
| GUI 交互界面 | Mac | wxPython |
| 实盘信号生成 | Mac | engine/strategy.py 策略逻辑 |
| **QMT 下单 / 撤单** | **Windows** | **通过 REST API 转发至 xttrader** |
| **QMT 账户/持仓查询** | **Windows** | **通过 REST API 转发至 xttrader** |
| **QMT 行情快照 / K线** | **Windows** | **通过 REST API 转发至 xtdata** |

### 5.2 Windows 服务功能边界

`windows_service/` 是一个**独立的 Flask REST API 服务**，功能边界严格限定为：

**✅ 包含（QMT 接口代理）：**
- `xttrader` 交易接口：下单（同步/异步）、撤单、查询资产/持仓/委托/成交
- `xtdata` 行情接口：K线历史、Tick 快照、合约信息、交易日历、板块、指数权重、财务数据

**❌ 不包含（全部在 Mac 端）：**
- 策略逻辑 / 算子系统
- 回测引擎（Backtrader Cerebro）
- 数据拉取（Tushare）
- DuckDB 数据库操作
- 因子计算 / 绩效分析
- GUI 界面

### 5.3 通信协议

```
Mac 端（策略信号）  ──HTTP POST──▶  Windows 端（windows_service）
                                     api_server.py:8080
                                          │
                          ┌──────────────┴──────────────┐
                          ▼                             ▼
                   xttrader.order_stock()    xtdata.get_market_data()
                   （下单/查询）              （行情数据）
```

- 认证：HTTP Header `X-API-Token`（可选，通过 `config.API_TOKEN` 配置）
- 数据格式：JSON
- 默认端口：`8080`（可通过环境变量 `API_PORT` 覆盖）

### 5.4 Windows 端部署步骤

```cmd
# 1. 确认 MiniQMT 已启动并登录
# 2. 修改 windows_service/config.py
#    QMT_PATH    = r'D:\迅投极速交易终端\userdata_mini'
#    QMT_ACCOUNT = '1000000365'

# 3. 检查环境
python windows_service/check_env.py

# 4. 启动服务
python windows_service/run_service.py

# 5. 放行防火墙端口
netsh advfirewall firewall add rule name="QMT API" dir=in action=allow protocol=tcp localport=8080
```

### 5.5 Mac 端调用示例

```python
from windows_service.mac_client_example import QMTClient

client = QMTClient(host='192.168.1.100', port=8080, token='')

# 查询账户资产
asset = client.query_asset()

# 下单
result = client.order('511220.SH', 'buy', 1000)

# 查询持仓
positions = client.query_positions()
```

详细 API 文档见 `windows_service/README.md`。

---

## 六、使用示例

### 6.1 拉取数据

```python
from pull_tushare.main import run_pull
run_pull()  # 多线程拉取全部数据
```

### 6.2 ETF 风险平价策略回测

```python
from engine.strategy import Engine
from engine.proj_config import ProjConfig
from engine.algos.algos_date import RunWeekly
from engine.algos.algos_select import SelectAll
from engine.algos.algos_weight import WeightERC
from engine.algos.algos_balance import Rebalance
from engine.algos.algos_debug import PrintDate

proj = ProjConfig()
proj.name = "ETF风险平价"
proj.start_date = "2020-01-01"
proj.end_date = "2024-12-31"
proj.symbols = [
    '511220.SH',   # 城投债ETF
    '518880.SH',   # 黄金ETF
    '513500.SH',   # 标普500ETF
]
proj.benchmark = '513500.SH'
proj.algos = [
    PrintDate(),
    RunWeekly(),
    SelectAll(),
    WeightERC(),
    Rebalance(),
]

engine = Engine(proj)
engine.run()
engine.analysis(console=True)
```

### 6.3 查询数据库

```python
from orm_models.api import DataApi
from orm_models.table_models.stock_trade import Daily

api = DataApi()
df = api.read(Daily, symbols=['000001.SZ'], start='2024-01-01', end='2024-12-31')
```

### 6.4 因子计算

```python
from datafeed.expr import calc_expr

# 在 DataFrame 上计算自定义因子
df['ret_5d'] = calc_expr(df, "close/shift(close,5)-1")
df['sma_20'] = calc_expr(df, "ta_sma(close,20)")
```

### 6.5 启动 GUI

```bash
python main.py
```

---

## 七、策略项目配置文件

策略配置存放在 `data/projs/` 目录下，使用 TOML 格式：

```toml
[strategy]
name = "ETF风险平价"
start_date = "2020-01-01"
end_date = "2024-12-31"
commission = 0.001
slippage = 0.001
benchmark = "513500.SH"

[strategy.symbols]
codes = ["511220.SH", "518880.SH", "513500.SH"]

[[strategy.algos]]
name = "RunWeekly"

[[strategy.algos]]
name = "SelectAll"

[[strategy.algos]]
name = "WeightERC"

[[strategy.algos]]
name = "Rebalance"
```

---

## 八、扩展开发指南

### 8.1 添加新数据表

1. 在 `orm_models/table_models/` 中定义 SQLAlchemy 模型
2. 在 `orm_models/register.py` 中注册
3. 在 `pull_tushare/tushare_tables/` 中实现拉取类
4. 继承 `MetaDataBase`（元数据）或 `DetailDataBase`（明细数据）

### 8.2 添加新算子

1. 在 `engine/algos/` 下创建或编辑文件
2. 继承 `Algo` 基类，实现 `__call__(self, target)` 方法
3. 通过 `target.temp` 字典在算子间传递数据
4. 返回 `True` 继续 / `False` 停止

### 8.3 添加新因子函数

1. 在 `datafeed/expr_funcs.py` 中添加函数
2. 函数签名：接收 `pd.Series` 和参数，返回 `pd.Series`
3. 在表达式字符串中即可直接使用

### 8.4 添加新机器学习模型

1. 在 `engine/models/` 中继承 `model_base.py` 的基类
2. 实现 `train()` 和 `predict()` 方法
3. 在 `algos_model.py` 中调用

---

## 九、回测框架对比：PyBroker vs Backtrader

本项目经历了从 PyBroker 到 Backtrader 的迁移，此处记录两者的核心差异，作为技术决策依据。

### 9.1 核心定位

| 维度 | PyBroker | Backtrader |
|------|----------|------------|
| 发布时间 | 2023 年（较新） | 2015 年（成熟） |
| 执行模型 | 向量化（批量处理历史数据） | 事件驱动（逐 bar 推进） |
| 实盘支持 | ❌ 无 | ✅ live 模式，原生支持接入券商 |
| 社区生态 | 较小，文档不完善 | 大，第三方扩展多 |
| 代码复杂度 | 低，API 简洁 | 中高，概念多（Cerebro/Feed/Sizer/Analyzer） |

### 9.2 PyBroker 优势

- **API 简洁**：`strategy.backtest()` 一行跑完，结果直接返回 DataFrame
- **内置 ML 支持**：原生集成特征工程、模型训练、walk-forward 验证
- **向量化性能好**：批量计算，回测速度快
- **结果对象丰富**：`result.orders` / `result.positions` / `result.portfolio` 开箱即用

```python
# PyBroker 风格：简洁
strategy = StrategyAlgos(config)
result = strategy.backtest()
print(result.portfolio)
```

### 9.2.5 PyBroker 劣势

- **❌ 无实盘支持**：纯回测框架，不支持 live 模式，无法直接接入券商交易
  - 若要实盘，只能：定时跑回测 → 提取持仓 → 调用券商 API 下单（外挂方案，无法反馈成交状态）
  - 信号与执行脱离，无法处理部分成交、滑点等实盘情况
- **事件驱动不完善**：向量化回测无法还原逐 bar 订单状态变化（notify_order/notify_trade）
- **生态较小**：文档不完善，bug 反馈周期长
- **结果对象固定**：DataFrame 格式难以扩展自定义指标

### 9.3 Backtrader 优势

- **实盘 live 模式**：Cerebro 支持接入真实券商（QMT、IB、OANDA 等），回测代码无需改动即可切换实盘
- **事件驱动更接近真实**：逐 bar 执行，`notify_order` / `notify_trade` 处理订单状态，与实盘行为一致
- **成熟稳定**：经过多年生产验证，边界情况处理完善
- **扩展性强**：Analyzer、Observer、Sizer 等扩展点齐全

```python
# Backtrader 风格：回测与实盘同一套代码
cerebro = bt.Cerebro()
cerebro.addstrategy(StrategyAlgo, algo_list=[...])
# 回测模式：adddata(bt.feeds.PandasData(...))
# 实盘模式：adddata(QMTData(...))
cerebro.run()
```

### 9.4 本项目的选择

**底层引擎用 Backtrader，算子组合模式借鉴 bt 库。**

| 层次 | 方案 | 理由 |
|------|------|------|
| 执行引擎 | Backtrader (`bt.Strategy.next()`) | 唯一支持 QMT live 模式的成熟方案 |
| 策略组合 | `Algo` / `AlgoStack` 模式（来自 [bt 库](https://github.com/pmorissette/bt)） | 模块化、可复用、易测试，算子链逻辑清晰 |
| 遗留代码 | `engine/engine.py`（PyBroker 版）| 仍被 GUI 和部分脚本引用，待迁移至 Backtrader |

**迁移方向（P0）：**
```
当前（过渡期）：
  engine/engine.py   → PyBroker，GUI 主路径（待迁移）
  engine/strategy.py → Backtrader，新版核心，逐步接管

目标：
  统一使用 engine/strategy.py（Backtrader）
  删除 engine/engine.py 中的 PyBroker 依赖
```

---

## 十、依赖环境

主要 Python 依赖：

```
# Mac 端（主环境）
pandas
numpy
sqlalchemy
duckdb-engine
tushare
backtrader
bokeh
wxPython
loguru
pendulum
ta-lib
lightgbm
autogluon
ffn
scipy

# Windows 端（windows_service/）
flask
flask-cors
loguru
# xtquant（随 MiniQMT 客户端安装，不通过 pip）
```

---

## 十一、注意事项

1. **Tushare Token**：需在 `config.py` 中配置有效的 Tushare Pro Token，部分接口需要较高权限
2. **DuckDB 文件**：默认数据库文件为 `data/duck.db`，不应纳入版本控制
3. **API 频率限制**：Tushare 有调用频率限制，`pull_tushare` 已内置等待机制
4. **复权处理**：行情数据默认不复权，需通过 `adj_factor` 表进行前/后复权计算
5. **TA-Lib**：需要单独安装系统级 TA-Lib 库，再安装 Python 包装器
6. **QMT 实时交易时段**：xttrader 下单仅在 A 股交易时段内有效，Mac 端策略触发实盘前须校验时间

   | 时段 | 时间 |
   |------|------|
   | 集合竞价（可撤单） | 09:15 - 09:20 |
   | 集合竞价（锁定） | 09:20 - 09:25 |
   | 上午开盘 | 09:30 - 11:30 |
   | 下午开盘 | 13:00 - 15:00 |
   | 收盘集合竞价（深市）| 14:57 - 15:00 |

   周末及法定节假日休市。非交易时段 `get_full_tick` 返回空数据属正常现象。

---

## 十二、前端框架规划：Web 服务取代 wxPython GUI

### 12.1 决策背景

项目早期使用 wxPython 构建桌面 GUI（`gui/` 目录），但随着以下问题暴露，决定转向 Web 服务方案：

| 问题 | 说明 |
|------|------|
| Bokeh 嵌入成本高 | wxPython 内嵌 Bokeh 图表须走 WebView，本质仍是浏览器内核，多此一举 |
| wxPython 安装困难 | macOS 上频繁出现 wheel 不兼容问题，需 conda 或手动编译 |
| 架构不一致 | Mac 端桌面 App + Windows REST 服务，两种范式增加维护成本 |
| 无法远程访问 | 回测运行期间无法从其他设备查看结果 |

**决策：废弃 wxPython GUI，全面改用 Web 服务（Python HTTP + Bokeh + 原生 JS）。**

`stock_trend_service.py` 已验证方案可行，作为 Web 层的参考实现。

---

### 12.2 整体架构

```
╔══════════════════════════════════════════════════════════════════╗
║                    Mac 端 Web 服务层                              ║
║                                                                  ║
║   浏览器（任意设备）                                               ║
║       │  HTTP                                                    ║
║       ▼                                                          ║
║   web_service/                                                   ║
║   ├── server.py          HTTP 路由入口（stdlib http.server）       ║
║   ├── handlers/          各路由处理器                             ║
║   │   ├── chart.py       /chart     股票池趋势图                  ║
║   │   ├── backtest.py    /backtest  回测触发 + 结果展示            ║
║   │   ├── positions.py   /positions 持仓/委托（转发 QMT 服务）     ║
║   │   └── config.py      /config    策略参数配置                  ║
║   └── templates/         HTML 模板（复用 stock_trend_service 风格）║
║                                                                  ║
║   已有模块（不变）                                                 ║
║   ├── engine/            回测引擎 + 算子系统                       ║
║   ├── datafeed/          数据加载 + 因子计算                       ║
║   └── orm_models/        数据库 ORM                              ║
╚══════════════════════════════════════════════════════════════════╝
                │ HTTP REST API
╔═══════════════╪══════════════════════════════════════════════════╗
║  Windows 端   ↓                                                  ║
║   windows_service/api_server.py（Flask，端口 8080）              ║
╚══════════════════════════════════════════════════════════════════╝
```

---

### 12.3 路由规划

| 路由 | 方法 | 功能 | 实现状态 |
|------|------|------|----------|
| `/` | GET | 重定向至 `/chart?period=3` | ✅ 已实现 |
| `/chart` | GET | 股票池归一化趋势图（总览） | ✅ 已实现 |
| `/industry` | GET | 申万L1行业分组趋势图 | ✅ 已实现 |
| `/backtest` | GET | 回测参数配置页面 | 待开发 |
| `/backtest/run` | POST | 触发回测，返回任务 ID | 待开发 |
| `/backtest/result/<id>` | GET | 回测结果页（Bokeh 绩效图） | 待开发 |
| `/positions` | GET | 当前持仓/委托查询 | 待开发 |
| `/order` | POST | 手动下单（转发 QMT 服务） | 待开发 |

---

### 12.4 技术选型

| 层次 | 技术 | 理由 |
|------|------|------|
| HTTP 服务 | Python `stdlib http.server` | 零依赖，已验证，无需引入 Flask/FastAPI |
| 图表渲染 | Bokeh `components()` + CDN | 与回测引擎的 `show_results.py` 统一，无需额外依赖 |
| 前端交互 | 原生 JS（无框架） | 交互逻辑简单（checkbox 联动、搜索过滤），无需 React/Vue |
| 样式 | 内联 CSS（Catppuccin Mocha 配色） | 与现有页面风格一致，无 CSS 框架依赖 |
| 异步回测 | Python `threading.Thread` | 回测耗时较长，需后台执行，结果轮询或 SSE 推送 |

> 如后续路由复杂度显著上升（>10 个端点），可迁移至 **FastAPI**（保持 Pydantic 类型安全，自动生成 OpenAPI 文档）。当前阶段不引入。

---

### 12.5 回测页面交互流程

```
用户填写策略参数（/backtest 页面）
        │ POST /backtest/run
        ▼
server 接收参数 → 后台 Thread 执行 Engine.run()
        │ 返回 {"task_id": "xxx", "status": "running"}
        ▼
前端轮询 GET /backtest/result/xxx
        │ status=running → 显示进度条
        │ status=done    → 渲染 Bokeh 绩效图
        ▼
绩效图页面（净值曲线 / 回撤 / 指标表）
```

---

### 12.6 持仓页面数据流

```
浏览器 GET /positions
        │
        ▼
web_service/handlers/positions.py
        │ 调用 QMTClient（HTTP）
        ▼
Windows windows_service/api_server.py
        │ /api/query/positions → xttrader.query_stock_positions()
        ▼
返回 JSON → 前端渲染持仓表格
```

---

### 12.7 目录结构规划

```
stockanalysis/
├── web_service/                 # Web 服务层（新增，取代 gui/）
│   ├── server.py                # HTTP 服务入口，路由分发
│   ├── cache.py                 # 页面级缓存（period → html）
│   ├── handlers/
│   │   ├── chart_handler.py     # /chart、/industry（已在 stock_trend_service.py）
│   │   ├── backtest_handler.py  # /backtest、/backtest/run、/backtest/result/<id>
│   │   ├── position_handler.py  # /positions
│   │   └── order_handler.py     # /order
│   └── templates/
│       └── base.html            # 公共导航栏、CSS 变量（复用现有风格）
│
├── stock_trend_service.py       # 现阶段独立运行，后续逻辑迁入 web_service/
├── gui/                         # 废弃，暂不删除（等 web_service 稳定后移除）
└── main.py                      # 原 wxPython 入口，后续改为启动 web_service
```

---

### 12.8 迁移计划

| 阶段 | 任务 | 优先级 |
|------|------|--------|
| P0 | 将 `stock_trend_service.py` 的路由逻辑拆分迁入 `web_service/` | 高 |
| P0 | 实现 `/backtest` 页面：参数表单 + 后台执行 + 结果轮询 | 高 |
| P1 | 实现 `/positions` 页面：持仓/委托表格（依赖 Windows QMT 服务） | 中 |
| P1 | 抽取公共 `base.html` 导航栏模板，统一各页面风格 | 中 |
| P2 | 实现 `/order` 手动下单页面 | 低 |
| P2 | 废弃 `gui/` 目录，`main.py` 改为 `web_service` 启动入口 | 低 |
