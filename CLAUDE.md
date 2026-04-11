# StockAnalysis 量化投研平台

## 项目简介
AI智能量化投研平台，用于股票/基金/指数数据管理、因子计算、策略回测与绩效分析。

## 技术栈
- 数据库：DuckDB + SQLAlchemy ORM
- 数据源：Tushare API
- 回测+实盘引擎：Backtrader（统一） + 自定义算子系统（engine/algos/）
- 实盘对接：QMT (xtquant) via Backtrader live 模式（backtrader_qmt_api/）
- Web 后端：Flask（api/ 目录，Blueprint 分模块路由）
- Web/桌面前端：Vue 3 + Vite + Electron（桌面端打包）
- 图表：ECharts（前端渲染，后端只返回 JSON）
- 日志：Loguru
- 日期处理：Pendulum

## 核心模块
- `engine/` - Backtrader 回测/实盘引擎 + 算子系统 + 绩效分析
- `engine/strategy.py` - StrategyAlgo（bt.Strategy + 算子链，核心策略类）
- `engine/algos/` - 算子系统（时间控制/选股/权重/再平衡/择时/网格）
- `backtrader_qmt_api/` - QMT Backtrader 桥接层（QMTStore/QMTBroker/QMTData，未跑通）
- `orm_models/` - SQLAlchemy ORM 表定义 + DataApi 统一数据访问层
  - `orm_models/table_models/` - 各业务表的 Model 类（按数据类型分子模块）
  - `orm_models/api.py` - DataApi 类、engine/session 单例、`init_db()` 建表函数
- `pull_tushare/` - Tushare 数据拉取（多线程，支持增量更新）
- `datafeed/` - 历史数据加载器（Duckdbloader）+ 因子表达式计算引擎
  - `datafeed/expr/` - 表达式引擎子包（expr.py、expr_funcs*.py、expr_rolling.py）
- `api/` - Flask Web 后端（Blueprint 分模块路由 + Handler 业务逻辑）
  - `api/stockpool.py` - 股票池工具（load_stockpool，供多个 handler 共用）
  - `api/cache.py` - 线程安全内存缓存，支持 TTL 过期
- `config.py` - 全局配置（DB_URI、Tushare token、get_pro() 懒加载）
- `clawspace/` - 用户自定义策略脚本工作区（algos/factors/projs/scripts），不纳入版本控制

## 关键约束
- QMT 客户端仅支持 Windows，Backtrader live 交易必须在 Windows 上运行
- 开发环境为 macOS，实盘部署需要 Windows 机器
- Tushare API 有调用频率限制，pull_tushare 已内置等待机制
- TA-Lib 需要单独安装系统级库

## 开发约定

### 代码风格
- Python 代码使用中文注释（项目面向中文用户）
- 日志使用 Loguru（`from loguru import logger`），不用 print 调试
- 日期字符串统一格式：`YYYY-MM-DD`（如 `2024-01-01`）
- 数据库表的日期字段为字符串类型，非 datetime

### 模块开发规范
- 数据表模型定义在 `orm_models/table_models/`，继承 SQLAlchemy Base
- 算子继承 `engine/algos/algo_base.py` 的 Algo 基类，实现 `__call__(self, target)` 方法
- 因子函数定义在 `datafeed/expr/expr_funcs*.py`，签名为 `func(pd.Series, *args) -> pd.Series`
- 策略配置使用 `engine/proj_config.py` 的 ProjConfig
- 数据拉取类继承 MetaDataBase（元数据）或 DetailDataBase（明细数据）
- 数据文件存放在 `data/` 目录，不纳入版本控制
- Tushare pro 实例通过 `from config import get_pro; pro = get_pro()` 获取（懒加载，避免导入副作用）
- 数据库建表在启动时由 `init_db()` 统一执行，不在 import 时自动触发

### 当前开发重点（P0）
统一 Backtrader 引擎 + QMT 模拟盘对接，详见 `docs/项目计划.md`

## 常用命令
```bash
# ── 后端 ──────────────────────────────────
python run.py                        # 启动 Flask 后端（端口 8888）
python run.py --no-stockpool         # 启动时不加载股票池（快速调试）
python pull_tushare/main.py          # 拉取 Tushare 数据

# ── 前端（开发）────────────────────────────
cd frontend && npm run dev           # 启动 Vite dev server（端口 5173）

# ── Electron 桌面端 ────────────────────────
npm run electron:dev                 # 启动 Electron 窗口（开发模式，需先启动后端和前端）
npm run frontend:build               # 构建 Vue → frontend/dist/
npm run electron:build               # 打包桌面安装包 → build/dist/
```

## 详细文档
- `docs/DEVELOPMENT.md` - 完整开发文档（架构、模块详解、示例）
- `docs/项目计划.md` - 项目规划和任务清单
- `docs/README.md` - 使用说明
