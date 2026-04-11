# StockAnalysis 量化投研平台 - 开发文档

## 一、项目概述

AI智能量化投研平台，用于股票/基金/指数数据管理、因子计算、策略回测与绩效分析。

**技术栈：**
- 数据库：DuckDB（SQLAlchemy ORM）
- 数据源：Tushare API
- 回测+实盘引擎：Backtrader（统一）+ 自定义算子系统
- 实盘对接：QMT (xtquant) via Windows REST API 服务
- Web 后端：Flask（Blueprint 分模块路由）
- Web 前端：Vue 3 + Vite
- 数据处理：Pandas、NumPy、TA-Lib
- 机器学习：AutoGluon、LightGBM
- 可视化：ECharts（前端渲染，后端只返回纯 JSON 数据）
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

---

## 十三、Web 前后端分离架构规划

### 13.1 技术选型决策

| 层 | 选型 | 备选 | 选择原因 |
|---|---|---|---|
| 后端框架 | **Flask** | FastAPI | 轻量，Blueprint 与现有 handler 分层天然对应；单用户本地场景无需 async 和 Pydantic 校验 |
| 前端框架 | **Vue 3 + Vite** | React | 学习曲线平缓，对 Python 开发者友好；单人开发，React 生态优势体现不出来 |
| 图表渲染 | **ECharts 前端渲染** | Bokeh 服务端 | 后端只返回纯数据 JSON，前端 ECharts 自主渲染；解耦彻底，无 CDN 外部依赖，Vue 集成自然 |
| 数据库 | **DuckDB** | PostgreSQL | 单用户本地，无多写冲突；单文件部署简单 |

### 13.2 目标目录结构

```
stockanalysis/
├── api/                        ← Flask 后端（替代现有 web_service/）
│   ├── app.py                  ← Flask app 工厂（create_app()）
│   ├── routes/
│   │   ├── chart.py            ← /api/chart/*
│   │   ├── industry.py         ← /api/industry/*
│   │   ├── backtest.py         ← /api/backtest/*
│   │   └── value.py            ← /api/value/*
│   └── handlers/               ← 现有 handler 逻辑基本不动（去掉 HTML 渲染）
│       ├── chart_handler.py
│       ├── backtest_handler.py
│       └── value_matrix_handler.py
│
└── frontend/                   ← Vue 3 + Vite
    ├── src/
    │   ├── views/              ← Chart.vue / Industry.vue / Backtest.vue / Value.vue
    │   ├── components/
    │   │   └── EChartsWrapper.vue  ← 通用 ECharts 容器（init/dispose/resize/option watch）
    │   └── router/             ← vue-router 路由配置
    ├── dist/                   ← 构建产物，提交到仓库（用户无需安装 Node）
    └── vite.config.js          ← 开发时代理 /api/* 到 Flask
```

### 13.3 开发模式 vs 生产模式

**开发时：**
```
Vite dev server (:5173) → 代理 /api/* → Flask (:5000)
热重载前端，Flask 同步调试
```

**生产/发布时：**
```
npm run build → dist/
Flask 静态托管 dist/，单进程单端口，无需 Nginx
```

### 13.4 分发策略与降低安装难度

**定位：开源自托管**
- 用户下载代码，填写自己的 Tushare token，本地运行
- 数据完全本地，不依赖外部服务
- 将来用户规模扩大后再考虑 SaaS（需换 PostgreSQL + 用户认证体系）

**降低安装门槛的措施（优先级排序）：**

| 措施 | 效果 | 说明 |
|---|---|---|
| `dist/` 提交到仓库 | 高 | 用户无需安装 Node.js/npm，直接 `pip install + python` 即可 |
| Docker 镜像 | 高 | `docker run` 一行启动，无需配置 Python 环境和依赖 |
| 一键启动脚本 | 中 | `start.sh`/`start.bat`，自动检测环境、初始化数据库、启动服务 |
| 引导式首次配置 | 中 | 首次启动自动检测 `config.py` 是否存在，不存在则提示填写 token |

### 13.5 现有代码迁移成本评估

`web_service/` 现有 handler 代码**几乎不需要改动**，主要改动点：

1. `server.py` 路由 → 换成 Flask Blueprint（约 50 行）
2. Handler 去掉 HTML 渲染部分，`return dict` 即可，Flask 自动转 JSON
3. 前端新建 Vue 项目，使用 ECharts 渲染图表，后端只提供纯数据 JSON

**迁移步骤（已完成）：**

| 步骤 | 内容 | 状态 |
|---|---|---|
| 1 | `web_service/` → `api/`，handler 改为返回 dict | ✅ 已完成 |
| 2 | 新建 Flask app.py，注册 Blueprint | ✅ 已完成 |
| 3 | `vue create frontend` + 配置 Vite 代理 | ✅ 已完成 |
| 4 | 安装 echarts，创建 EChartsWrapper.vue 通用组件 | ✅ 已完成 |
| 5 | 逐页面改写：Chart / Industry / Value 全部迁移至 ECharts | ✅ 已完成 |
| 6 | 移除 Bokeh CDN 依赖，后端 handler 去掉 bokeh import | ✅ 已完成 |
| 7 | `npm run build` → `dist/`，Flask 托管静态文件 | 待执行 |
| 8 | 提交 `dist/`，更新用户安装文档 | 待执行 |

---

## 十四、Bokeh → ECharts 迁移记录

### 14.1 迁移背景

初始设计采用 Bokeh 服务端渲染（`components()` 返回 `script + div`，前端注入 DOM）。
实际使用中暴露三类问题：

| 问题 | 具体表现 |
|---|---|
| CDN 依赖 | 需在 `index.html` 手动引入 Bokeh CDN（3 个 script），国内可能加载慢 |
| Vue 集成摩擦 | `v-if` 切换组件时 watch 触发时机不对（`immediate` 在 DOM 挂载前执行），导致图表空白 |
| 前后端耦合 | 改颜色/字体须修改 Python 代码并重启服务 |

### 14.2 迁移方案

**后端**：移除所有 `bokeh.embed` / `bokeh.plotting` / `bokeh.models` 导入，handler 直接返回纯数据 JSON。

| API 端点 | 迁移前返回 | 迁移后返回 |
|---|---|---|
| `GET /api/chart` | `{script, div, meta, count}` | `{dates, series:[{sym,name,color,values}], count}` |
| `GET /api/industry` | `{script, figures:[{name,count,div}], total}` | `{dates, groups:[{name,count,series}], total}` |
| `GET /api/value/data` | `{script, div, stocks, count}` | `{stocks:[{code,name,x,y}], count}` |
| `POST /api/value/forecast` | `{script, div}` | `{stocks:[{code,name,x,y}]}` |

**前端**：`npm install echarts`，新增 `EChartsWrapper.vue` 通用容器，三个页面改用 ECharts computed option 驱动渲染。

### 14.3 EChartsWrapper 设计

```
props.option（computed，响应式）
       ↓ watch deep
  chart.setOption(opt, { notMerge: true })
       ↓
  ECharts Canvas 自动重绘
```

- `onMounted` 初始化，`onBeforeUnmount` dispose + 移除 resize 监听
- `defineExpose({ getInstance })` 供父组件获取 chart 实例（如需 dispatchAction）
- 始终挂载，loading 用绝对定位遮罩覆盖（避免销毁重建时机问题）

### 14.4 颜色生成

移除 `bokeh.palettes`，改为纯 Python 实现：
- ≤20 只：使用 `_PALETTE_20`（Matplotlib tab20 等效色）
- >20 只：`colorsys.hls_to_rgb` HLS 均匀分布

---

## 十五、前端设计规范：Apple HIG 风格

### 15.1 设计原则来源

前端视觉系统参考 **Apple Human Interface Guidelines (HIG)**，核心理念：

| 原则 | 含义 | 在本项目的体现 |
|---|---|---|
| **Clarity（清晰）** | 文字清晰易读，图标精确，装饰服务于内容 | 细分隔线（0.5px）、极轻阴影、去掉多余边框 |
| **Deference（谦逊）** | UI 烘托内容，不喧宾夺主 | 白色背景、灰阶填充、accent 蓝仅用于主操作 |
| **Depth（层次）** | 视觉层次传递信息层级 | 卡片阴影、毛玻璃导航栏、面板与内容区分色 |

### 15.2 色彩系统（CSS 变量）

所有颜色定义在 `frontend/src/style.css` 的 `:root` 块，对应 Apple System Colors：

```css
/* 背景层级 */
--bg-primary:       #ffffff;   /* systemBackground */
--bg-secondary:     #f2f2f7;   /* secondarySystemBackground / systemGray6 */

/* 文字 */
--label:            #1c1c1e;   /* label（主文字） */
--label-muted:      #8e8e93;   /* quaternaryLabel / 辅助文字 */

/* 分隔线 */
--separator:        #c6c6c8;   /* separator */
--separator-opaque: #e5e5ea;   /* opaqueSeparator / systemGray5 */

/* 填充面（交互背景） */
--fill:             #78788014; /* systemFill（~8% 灰）*/
--fill-2:           #7878801e; /* secondarySystemFill */
--fill-3:           #74748028; /* tertiarySystemFill（按钮默认底色）*/
--fill-4:           #74748032; /* quaternarySystemFill（悬停底色）*/

/* 系统灰阶 */
--gray ~ --gray-6:  #8e8e93 → #f2f2f7  /* systemGray → systemGray6 */

/* 品牌主色 */
--accent:           #007aff;   /* systemBlue（Apple 签名蓝）*/
--accent-hover:     #0066d6;

/* 状态色 */
--green:            #34c759;   /* systemGreen */
--red:              #ff3b30;   /* systemRed */
--orange:           #ff9500;   /* systemOrange */
```

**使用原则**：
- 背景固定用 `--bg-primary`（白）/ `--bg-secondary`（浅灰），**不直接写颜色值**
- 交互元素 hover 用 `--fill-2`，默认底色用 `--fill-3`
- accent 蓝只用于**主操作按钮**、**激活状态**、**链接/选中**，其余保持灰色
- 危险操作用 `--red`，成功提示用 `--green`

### 15.3 字体规范

```css
--font-stack: -apple-system, 'SF Pro Display', 'SF Pro Text',
              'Helvetica Neue', Helvetica, Arial, sans-serif;
```

字号采用 Apple HIG 标准字阶（1pt ≈ 1px @1x）：

| 变量 | 尺寸 | 用途 |
|---|---|---|
| `--size-xs` | 11px | caption、标签、角标 |
| `--size-sm` | 13px | footnote、辅助文字 |
| `--size-body` | 15px | 正文（默认） |
| `--size-callout` | 16px | callout |
| `--size-headline` | 17px | 标题、按钮 |
| `--size-title3` | 20px | 三级页面标题 |
| `--size-title2` | 22px | 二级标题 |
| `--size-title1` | 28px | 一级标题 |
| `--size-large` | 34px | largeTitle |

### 15.4 间距系统（8pt 网格）

```css
--space-1: 4px   --space-2: 8px   --space-3: 12px  --space-4: 16px
--space-5: 20px  --space-6: 24px  --space-8: 32px  --space-10: 40px
```

所有内边距、外边距、间隙一律使用 `--space-*` 变量，不直接写 px。

### 15.5 圆角规范

```css
--radius-xs: 4px   /* 小控件：输入框、徽章 */
--radius-sm: 6px   /* 按钮、搜索框、Segmented Control */
--radius:   10px   /* 卡片、面板（Apple 卡片标准） */
--radius-lg: 12px  /* 大卡片、iframe */
--radius-xl: 16px  /* 弹出层、Sheet */
```

### 15.6 阴影规范

```css
--shadow-xs: 0 1px 2px rgba(0,0,0,.06)  /* 卡片默认 */
--shadow-sm: 0 2px 8px rgba(0,0,0,.08)  /* 卡片悬停、下拉 */
--shadow:    0 4px 16px rgba(0,0,0,.10) /* 弹出层、模态 */
```

### 15.7 导航栏规范

```
高度：44px（var(--nav-height)）
背景：rgba(255,255,255,0.85) + backdrop-filter: blur(20px) saturate(1.8)
底部分隔：border-bottom: 0.5px solid var(--separator-opaque)
```

- Logo 字重 600，`--size-headline`，靠左
- Logo 与菜单之间用 `0.5px × 16px` 竖线隔开
- 菜单项默认色 `--label-muted`，hover 时背景 `--fill-2`，激活时文字变 `--accent`（无背景高亮）
- **不使用** box-shadow（保持 Apple 轻量风格）

### 15.8 常用组件规范

#### Segmented Control（分段控制器）

```html
<div class="seg-ctrl">        <!-- 灰底容器 -->
  <button class="seg-btn active">选项一</button>   <!-- 激活：白色药片+阴影 -->
  <button class="seg-btn">选项二</button>
</div>
```

```css
.seg-ctrl  { background: var(--fill-3); border-radius: var(--radius-sm); padding: 2px; }
.seg-btn   { height: 24px; border-radius: 4px; font-size: var(--size-xs); }
.seg-btn.active { background: var(--bg-primary); box-shadow: var(--shadow-xs); font-weight: 500; }
```

#### 卡片（Card）

```css
.card {
  background: var(--bg-primary);
  border-radius: var(--radius);       /* 10px */
  box-shadow: var(--shadow-xs);
  overflow: hidden;
}
.card:hover { box-shadow: var(--shadow-sm); }  /* 悬停微抬 */
```

#### 主操作按钮

```css
.btn-primary {
  background: var(--accent);    /* #007aff */
  color: #ffffff;
  font-weight: 500;
  height: 32px;
  border-radius: var(--radius-sm);
}
.btn-primary:hover { background: var(--accent-hover); }
```

#### 弹出遮罩（Modal Overlay）

```css
.overlay {
  background: rgba(0,0,0,0.35);
  backdrop-filter: blur(8px) saturate(1.6);
}
.overlay-card {
  background: rgba(255,255,255,0.94);
  border-radius: var(--radius-xl);   /* 16px */
  box-shadow: var(--shadow);
}
```

#### 搜索框

```css
.search-wrap {
  background: var(--fill-3);
  border-radius: var(--radius-sm);
  height: 28px;
  /* 无边框，灰底，SVG 放大镜图标 */
}
```

### 15.9 ECharts 图表风格

所有图表统一使用以下配置，与 Apple 视觉系统保持一致：

```js
{
  backgroundColor: '#ffffff',
  tooltip: {
    backgroundColor: 'rgba(255,255,255,0.92)',
    borderColor: '#e5e5ea',
    borderWidth: 0.5,
    textStyle: { color: '#1c1c1e', fontSize: 12 },
  },
  xAxis: {
    axisLine:  { lineStyle: { color: '#e5e5ea', width: 0.5 } },
    axisTick:  { lineStyle: { color: '#e5e5ea' } },
    axisLabel: { color: '#8e8e93', fontSize: 11 },
    splitLine: { show: false },
  },
  yAxis: {
    axisLine:  { show: false },
    axisTick:  { show: false },
    axisLabel: { color: '#8e8e93', fontSize: 11 },
    splitLine: { lineStyle: { color: '#f2f2f7', width: 1 } },
  },
}
```

- 折线宽度：`1.2px`（细腻，Apple 风格）
- 散点图默认色：`#007aff`（accent blue），emphasis 用 `#5856d6`（systemPurple）
- 辅助参考线：`#c6c6c8` dashed，`0.8px`

### 15.10 禁止事项

| 禁止 | 原因 |
|---|---|
| 直接写颜色值（如 `color: #333`） | 破坏设计 token 一致性，难以统一维护 |
| 使用 `border: 1px solid`（实线 1px） | Apple 用 0.5px 分隔线，视觉更轻 |
| box-shadow 用于导航栏 | Apple nav 只用底部 border，不加投影 |
| 圆角超过 `--radius-xl`（16px） | 超出 Apple HIG 规范范围 |
| accent 蓝用于非主操作 | 蓝色过多会稀释视觉重心 |
| 在 `style.css` 之外定义全局 CSS 变量 | 所有 token 集中管理 |

---

## 十六、桌面端发布规划：Electron 迁移

### 16.1 迁移动机

| 现状痛点 | Electron 解决方案 |
|---|---|
| 用户需手动开浏览器访问 `localhost:5173` | 程序启动即自动打开独立窗口，无需浏览器 |
| 无法生成可分发的 `.app` / `.exe` 安装包 | `electron-builder` 一键打包，支持 macOS/Windows |
| Python 环境依赖用户自行安装 | PyInstaller 将 Flask 后端打包成独立可执行文件，随安装包分发 |
| 无系统托盘、无原生菜单 | Electron 提供完整原生菜单栏、Dock 图标、系统托盘支持 |
| 文件选择/路径输入体验差 | 调用 Electron 原生 `dialog.showOpenDialog()` |

### 16.2 目标架构

```
┌──────────────────────────────────────────────────────┐
│                  Electron 主进程 (main.js)             │
│                                                      │
│  ① 启动 Flask 子进程（bundled Python binary）         │
│     spawn('python-backend', ['run.py', '--port=8888'])│
│                                                      │
│  ② 创建 BrowserWindow，加载 dist/index.html           │
│     preload.js 注入安全的 IPC 桥接                    │
│                                                      │
│  ③ 监控子进程，App 退出时自动关闭后端                  │
└────────────────────┬─────────────────────────────────┘
                     │ HTTP  localhost:8888
┌────────────────────▼─────────────────────────────────┐
│              Flask 后端（Python 子进程）               │
│              api/ 目录，现有代码不动                   │
│              DuckDB data/duck.db  + Tushare API       │
└──────────────────────────────────────────────────────┘
                     ↑ fetch('/api/...')
┌────────────────────┴─────────────────────────────────┐
│           Vue 3 渲染进程（BrowserWindow）              │
│           frontend/dist/  静态文件（已构建）           │
│           ECharts 图表、Apple 风格 UI                  │
└──────────────────────────────────────────────────────┘
```

**核心设计决策**：Electron 与 Flask 之间**继续使用 HTTP**（`fetch('/api/...')`），而不是 IPC。原因：
- 前端代码**零改动**，所有 API 调用路径不变
- Flask 进程可独立调试，保留命令行模式兼容性
- 未来若需要 Web 版本，架构直接复用

### 16.3 目录结构变化

```
stockanalysis/
├── electron/                      ← 新增：Electron 主进程代码
│   ├── main.js                    ← 主进程入口：窗口创建、后端进程管理
│   ├── preload.js                 ← 安全桥接：暴露有限 API 给渲染进程
│   └── icons/                     ← 应用图标（.icns / .ico / .png）
│
├── frontend/                      ← 不动，仍为 Vue 3 + Vite
│   ├── src/
│   └── dist/                      ← 构建产物，Electron 直接加载
│
├── api/                           ← 不动，Flask 后端
│
├── package.json                   ← 项目根 package.json（Electron 依赖）
│                                     注意：与 frontend/package.json 分离
└── build/                         ← electron-builder 配置和产物
    ├── entitlements.mac.plist
    └── dist/                      ← 打包产物（.dmg / .exe / .AppImage）
```

### 16.4 关键文件设计

#### `electron/main.js`（主进程核心逻辑）

```javascript
const { app, BrowserWindow, shell } = require('electron')
const { spawn } = require('child_process')
const path = require('path')

let mainWindow = null
let backendProcess = null
const BACKEND_PORT = 8888

// ── 启动 Flask 后端 ──────────────────────────────────────
function startBackend() {
  // 生产包：调用 PyInstaller 打出的二进制；开发时：调用系统 python
  const isProd = app.isPackaged
  const bin    = isProd
    ? path.join(process.resourcesPath, 'backend', 'run')  // PyInstaller 产物
    : 'python'
  const args   = isProd ? [] : [path.join(__dirname, '../run.py')]

  backendProcess = spawn(bin, [...args, `--port=${BACKEND_PORT}`], {
    stdio: 'pipe',
    env: { ...process.env },
  })

  backendProcess.stdout.on('data', d => console.log('[backend]', d.toString()))
  backendProcess.stderr.on('data', d => console.error('[backend]', d.toString()))
  backendProcess.on('exit', code => console.log('[backend] 退出，code:', code))
}

// ── 等待后端就绪（轮询 /api/health） ─────────────────────
async function waitForBackend(timeout = 30000) {
  const start = Date.now()
  while (Date.now() - start < timeout) {
    try {
      const res = await fetch(`http://localhost:${BACKEND_PORT}/api/health`)
      if (res.ok) return true
    } catch {}
    await new Promise(r => setTimeout(r, 300))
  }
  throw new Error('后端启动超时')
}

// ── 创建窗口 ────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280, height: 800,
    minWidth: 900, minHeight: 600,
    titleBarStyle: 'hiddenInset',   // macOS：使用隐藏式标题栏
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,       // 安全：禁用 Node.js 访问
    },
  })

  // 生产：加载打包后的静态文件；开发：加载 Vite dev server
  const isDev = !app.isPackaged
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../frontend/dist/index.html'))
  }
}

app.whenReady().then(async () => {
  startBackend()
  await waitForBackend()
  createWindow()
})

app.on('before-quit', () => {
  backendProcess?.kill()
})
```

#### `electron/preload.js`（IPC 安全桥接）

```javascript
const { contextBridge, ipcRenderer } = require('electron')

// 只暴露必要的能力给渲染进程（Vue 前端）
contextBridge.exposeInMainWorld('electronAPI', {
  // 打开文件选择对话框（用于选择 stockpool.xlsx / toml 文件等）
  openFile: (options) => ipcRenderer.invoke('dialog:openFile', options),
  // 获取应用版本
  getVersion: () => ipcRenderer.invoke('app:getVersion'),
  // 在系统浏览器中打开外部链接
  openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url),
})
```

### 16.5 Flask 后端打包（PyInstaller）

```bash
# 安装
pip install pyinstaller

# 打包 Flask 后端为单目录可执行文件（推荐 --onedir，比 --onefile 启动快）
pyinstaller run.py \
  --name python-backend \
  --onedir \
  --add-data "stockpool.xlsx:." \
  --add-data "data:data" \
  --hidden-import tushare \
  --hidden-import duckdb \
  --hidden-import flask \
  --distpath electron/resources/
```

注意事项：
- `--add-data` 需包含 `stockpool.xlsx`、初始数据库（可选）
- TA-Lib 等有 C 扩展的库需在**目标平台**上打包（macOS 打包 `.app`，Windows 打包 `.exe`）
- 首次打包需在 macOS 和 Windows 各执行一次

### 16.6 Electron 打包（electron-builder）

根目录 `package.json` 关键配置：

```json
{
  "name": "dadao-quant",
  "version": "1.0.0",
  "main": "electron/main.js",
  "scripts": {
    "electron:dev":   "electron .",
    "electron:build": "electron-builder",
    "frontend:build": "cd frontend && npm run build"
  },
  "devDependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.0.0"
  },
  "build": {
    "appId": "com.dadao.quant",
    "productName": "大道量化投研平台",
    "directories": { "output": "build/dist" },
    "files": [
      "electron/**",
      "frontend/dist/**",
      "!node_modules"
    ],
    "extraResources": [
      { "from": "electron/resources/python-backend", "to": "backend" }
    ],
    "mac": {
      "target":   [{ "target": "dmg", "arch": ["arm64", "x64"] }],
      "icon":     "electron/icons/icon.icns",
      "category": "public.app-category.finance"
    },
    "win": {
      "target": [{ "target": "nsis", "arch": ["x64"] }],
      "icon":   "electron/icons/icon.ico"
    }
  }
}
```

### 16.7 开发工作流

```
# 开发时（三端同时运行）
终端1：python run.py                          # Flask 后端
终端2：cd frontend && npm run dev             # Vite 前端热重载
终端3：npm run electron:dev                   # Electron 窗口（加载 :5173）

# 构建发布包
npm run frontend:build                        # 构建 Vue → dist/
pyinstaller ...（见 16.5）                    # 打包 Flask → electron/resources/
npm run electron:build                        # 打包 Electron → build/dist/
```

### 16.8 /api/health 健康检查接口

主进程需要轮询后端是否就绪，Flask 需增加一个轻量接口：

```python
# api/routes/health.py
from flask import Blueprint, jsonify
bp = Blueprint('health', __name__)

@bp.get('/health')
def health():
    return jsonify({'status': 'ok'})
```

注册到 `create_app()` 中：`app.register_blueprint(health_bp, url_prefix='/api')`

### 16.9 迁移步骤与优先级

| 步骤 | 内容 | 优先级 | 状态 |
|---|---|---|---|
| 1 | 根目录 `package.json` + 安装 electron | P0 | ✅ 已完成 |
| 2 | `electron/main.js`：窗口创建 + 加载 Vite dev URL | P0 | ✅ 已完成 |
| 3 | `electron/preload.js`：暴露 openFile 等原生 API | P0 | ✅ 已完成 |
| 4 | 增加 `/api/health` 接口 | P0 | ✅ 已完成 |
| 5 | main.js 启动/监控 Flask 子进程 | P1 | ✅ 已完成 |
| 6 | `vite.config.js` 调整 base 为 `'./'`（Electron file:// 兼容） | P1 | ✅ 已完成 |
| 7 | 制作应用图标（.icns / .ico） | P2 | ⬜ 待执行 |
| 8 | PyInstaller 打包 Flask 后端 | P2 | ⬜ 待执行 |
| 9 | electron-builder 生成 .dmg / .exe | P2 | ⬜ 待执行 |
| 10 | macOS 签名与公证（Apple Developer 证书） | P3 | ⬜ 待执行 |
| 11 | Windows 代码签名 | P3 | ⬜ 待执行 |

> **P0/P1**：已全部完成（开发模式可用）；**P2**：生成可分发安装包；**P3**：可上架/无安全警告

### 16.10 现有代码兼容性评估

| 模块 | 改动量 | 说明 |
|---|---|---|
| `api/routes/health.py` | **新增** | `/api/health` 健康检查，约 10 行 |
| `api/app.py` | **极小** | 注册 health blueprint，1 行 |
| `frontend/vite.config.js` | **小** | build 时 base 改为 `'./'`，兼容 file:// 协议 |
| `frontend/src/`（Vue） | **零** | HTTP fetch 路径完全不变 |
| `run.py` | **零** | 命令行启动方式保留，兼容 Electron 子进程调用 |
| `electron/main.js` | **新建** | 主进程：窗口 + 子进程管理 + IPC，约 160 行 |
| `electron/preload.js` | **新建** | 安全桥接，约 40 行 |
| 根 `package.json` | **新建** | Electron + electron-builder 依赖配置 |

**保留 Web 模式**：Electron 化后，`python run.py` + 浏览器访问的方式**依然有效**，两种模式共存，不影响现有开发习惯。
