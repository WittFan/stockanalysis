---
name: stockanalysis
description: >
  量化投研平台助手。当用户想要使用 StockAnalysis 量化投研框架、
  进行 A 股数据分析、编写回测策略、开发选股因子、查看行情图表，
  或者希望在不修改框架代码的前提下扩展量化工具时，激活此技能。
version: 1.0.0
metadata:
  openclaw:
    emoji: "📈"
    homepage: https://github.com/WittFan/stockanalysis
    requires:
      bins:
        - git
        - python3
---

## 关于本平台

StockAnalysis 是一个基于 **Backtrader + DuckDB** 的开源量化投研框架，提供：

- **Web 行情服务**：启动后通过浏览器访问，查看个股趋势、行业轮动
- **策略回测**：Backtrader 引擎 + 算子链，通过 TOML 配置运行回测
- **因子计算**：表达式引擎，支持自定义因子
- **数据管理**：Tushare 多线程增量拉取，DuckDB 本地存储

---

## 工作区间（Clawspace）

**所有新建和修改的文件，只在 `clawspace/` 目录内操作。框架核心代码不修改。**

```
clawspace/
├── algos/       ← 自定义算子（继承 Algo 基类）
├── factors/     ← 自定义因子函数（注册到表达式引擎）
├── projs/       ← 策略配置 TOML（回测参数）
└── scripts/     ← 一次性分析脚本
```

禁止修改的目录：`engine/` `orm_models/` `datafeed/` `web_service/` `pull_tushare/` `windows_service/`

---

## 初始化（仅首次，按顺序执行）

### 第一步：下载代码

```bash
git clone https://github.com/WittFan/stockanalysis.git
cd stockanalysis
pip install -r requirements.txt
```

### 第二步：配置

```bash
cp config_default.py config.py
```

编辑 `config.py`，填入：

```python
TUSHARE_TOKEN = 'your_tushare_token'   # https://tushare.pro 注册获取
```

> 仅需实盘时才配置 `QMT_SERVICE_HOST` 和 `QMT_SERVICE_TOKEN`

### 第三步：初始化数据库

```bash
python orm_models/register.py
```

### 第四步：拉取数据

```bash
python pull_tushare/main.py
```

### 第五步：启动服务

```bash
python main.py
```

浏览器访问 **http://localhost:8888**

---

## 日常使用

### 查看行情 / 行业分析
直接告诉我，我会帮你启动服务并说明如何访问。

### 运行回测
```
帮我在 clawspace/projs/ 下新建一个回测配置，用沪深300成分股，
2020年至今，每月换仓，按动量选前20只
```

### 扩展算子
```
帮我在 clawspace/algos/ 下写一个均线金叉选股算子
```
算子模板（继承 Algo 基类，实现 `__call__`）：
```python
from engine.algos.algo_base import Algo

class MyAlgo(Algo):
    def __init__(self, ...):
        ...

    def __call__(self, target) -> bool:
        # 返回 True 表示继续执行算子链，False 表示中断
        ...
        return True
```

### 扩展因子
```
帮我在 clawspace/factors/ 下注册一个自定义动量因子
```
因子函数签名固定为 `(pd.Series, *args) -> pd.Series`：
```python
import pandas as pd
from datafeed.expr import register_func

def momentum(series: pd.Series, window: int) -> pd.Series:
    return series.pct_change(window)

register_func('momentum', momentum)
```

### 临时分析脚本
```
帮我在 clawspace/scripts/ 下写一个脚本，统计过去一年行业涨跌幅排名
```

---

## 约定（来自 CLAUDE.md）

- 代码注释用**中文**
- 日志用 `from loguru import logger`，不用 print
- 日期字符串统一格式 `YYYY-MM-DD`
- 算子继承 `engine/algos/algo_base.py` 的 `Algo` 基类
- 因子签名：`func(pd.Series, *args) -> pd.Series`

---

## 参考文档

- 完整架构说明：`docs/DEVELOPMENT.md`
- 项目规划：`docs/项目计划.md`
- 项目约定：`CLAUDE.md`
