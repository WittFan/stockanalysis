# StockAnalysis 量化投研平台

AI 智能量化投研平台，用于股票/基金/指数数据管理、因子计算、策略回测与绩效分析。

---

## 快速开始

### 第一步：配置 Mac 端

```bash
cp config_default.py config.py
```

编辑 `config.py`，填入实际值：

```python
TUSHARE_TOKEN = 'your_tushare_token'     # https://tushare.pro 注册获取
QMT_SERVICE_HOST  = '192.168.1.100'      # Windows 机器局域网 IP（仅实盘需要）
QMT_SERVICE_TOKEN = 'your_shared_token'  # 与 Windows 端 API_TOKEN 保持一致
```

### 第二步：配置 Windows 端（仅实盘）

在 Windows 机器上：

```bash
cp windows_service/config_default.py windows_service/config.py
```

编辑 `windows_service/config.py`，填入实际值：

```python
QMT_PATH    = r'C:/国金QMT交易端模拟/userdata_mini'
QMT_ACCOUNT = '55003046'
API_TOKEN   = 'your_shared_token'   # 必须与 Mac 端 QMT_SERVICE_TOKEN 一致
```

生成共享 Token：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 第三步：初始化数据库

```bash
python orm_models/register.py
```

### 第四步：拉取 Tushare 数据

```bash
python pull_tushare/main.py
```

### 第五步：启动 Web 服务

```bash
python main.py
```

浏览器访问 http://localhost:8888

---

## 项目概述

| 功能 | 说明 |
|------|------|
| 数据管理 | Tushare 多线程增量拉取，DuckDB 存储 |
| 因子计算 | 表达式引擎（`datafeed/expr.py`），支持自定义因子 |
| 策略回测 | Backtrader 引擎 + 算子链（`engine/algos/`） |
| 可视化 | Web 服务（Bokeh 交互图表，浏览器访问） |
| 实盘交易 | QMT Windows 服务 + Mac REST API 调用 |

## 技术栈

- **数据库**：DuckDB + SQLAlchemy ORM
- **数据源**：Tushare Pro API
- **回测引擎**：Backtrader + 自定义算子系统
- **实盘对接**：QMT（xtquant，仅 Windows）via REST API
- **Web 服务**：Python stdlib `http.server` + Bokeh 图表

## 目录结构

```
stockanalysis/
├── config.py               # Mac 端配置（本地，不上传）
├── config_default.py       # Mac 端配置模板（GitHub）
├── main.py                 # 入口：启动 Web 服务
├── engine/                 # Backtrader 回测/实盘引擎 + 算子系统
├── orm_models/             # 数据库 ORM 层，DataApi 统一数据接口
├── pull_tushare/           # Tushare 数据拉取（多线程，支持增量）
├── datafeed/               # 数据加载 + 表达式因子计算引擎
├── web_service/            # Web 服务（图表/行业/回测页面）
├── windows_service/        # QMT 交易 REST API（Windows 部署）
└── data/                   # 数据目录（本地，不上传）
```

## 详细文档

- `docs/DEVELOPMENT.md` — 完整开发文档（架构、模块详解、Web 服务、部署）
- `docs/项目计划.md` — 项目规划和任务清单
