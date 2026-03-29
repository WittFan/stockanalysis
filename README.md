# StockAnalysis 量化投研平台

基于 Backtrader + DuckDB 的开源量化投研框架，提供数据管理、因子计算、策略回测与行情可视化。
---

## 快速开始

---

### 一、OpenClaw

[OpenClaw](https://github.com/openclaw/openclaw) 是运行在本地的开源 AI Agent 平台，以本地 Gateway 为核心，支持通过微信、Telegram、飞书、VSCode 等任意入口交互，数据不出本机，支持接入 Claude / Kimi / DeepSeek / OpenAI 等模型。

#### 已安装 OpenClaw 的用户，在对话框发送：

```
从 https://github.com/WittFan/stockanalysis 下载代码，
阅读 clawspace/SKILL.md，将其安装为 stockanalysis skill。
```

龙虾会自动完成代码拉取、环境配置、数据库初始化和服务启动，
后续所有操作限定在 `clawspace/` 目录内，不触碰框架代码。

### 二、Claude Code
[Claude Code](https://docs.anthropic.com/claude-code) 是 Anthropic 官方终端 AI 工具，在项目目录内直接对话，可读写文件、执行命令、全局理解代码。
AI 助手可直接读取项目内置的 `CLAUDE.md` 和 `docs/DEVELOPMENT.md`，理解架构后帮你完成配置、启动、调试、扩展。
已配置 Claude Code 的用户，在项目目录启动后发送：

```
git clone https://github.com/WittFan/stockanalysis.git 并阅读 README.md 和 CLAUDE.md，帮我完成初始化配置和启动。
```

---

### 三、VSCode + Kimi

[Kimi](https://kimi.moonshot.cn/) 
已配置 Kimi 编程工具的用户，发送：

```
从 https://github.com/WittFan/stockanalysis 拉取代码，阅读 README.md，帮我完成初始化配置和启动。
```

---

### 四、古法编程启动（手动操作）

#### 第一步：配置 Mac 端

```bash
cp config_default.py config.py
```

编辑 `config.py`：

```python
TUSHARE_TOKEN     = 'your_tushare_token'   # https://tushare.pro 注册获取
QMT_SERVICE_HOST  = '192.168.1.100'        # Windows 机器 IP（仅实盘需要，可跳过）
QMT_SERVICE_TOKEN = 'your_shared_token'    # 与 Windows 端 API_TOKEN 一致
```

#### 第二步：配置 Windows 端（仅实盘，可跳过）

```bash
cp windows_service/config_default.py windows_service/config.py
```

编辑 `windows_service/config.py`：

```python
QMT_PATH    = r'C:/国金QMT交易端模拟/userdata_mini'
QMT_ACCOUNT = '你的账号'
API_TOKEN   = 'your_shared_token'
```

生成共享 Token：
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

#### 第三步：安装依赖

```bash
pip install -r requirements.txt
```

#### 第四步：初始化数据库

```bash
python orm_models/register.py
```

#### 第五步：拉取 Tushare 数据

```bash
python pull_tushare/main.py
```

#### 第六步：启动 Web 服务

```bash
python main.py
# 或指定端口
python main.py --port 8888
```

浏览器访问 **http://localhost:8888**

---

## DIY 扩展

> 核心原则：**框架内部代码不修改，所有扩展挂载在外部。**

## 目录结构

```
stockanalysis/
├── SKILL.md                # OpenClaw 技能定义（AI Agent 入口）
├── CLAUDE.md               # 项目约定（AI 助手通用）
├── config.py               # Mac 端配置（本地，不上传）
├── config_default.py       # Mac 端配置模板（GitHub）
├── main.py                 # 入口：启动 Web 服务
│
├── clawspace/              # ← AI Agent 工作区间（仅此目录可写）
│   ├── algos/              #   自定义算子
│   ├── factors/            #   自定义因子函数
│   ├── projs/              #   策略配置 TOML
│   └── scripts/            #   一次性分析脚本
│
├── engine/                 # 【框架核心，不修改】回测引擎 + 算子系统
├── orm_models/             # 【框架核心，不修改】数据库 ORM 层
├── pull_tushare/           # 【框架核心，不修改】Tushare 数据拉取
├── datafeed/               # 【框架核心，不修改】数据加载 + 因子引擎
├── web_service/            # 【框架核心，不修改】Web 服务
├── windows_service/        # QMT 交易 REST API（Windows 部署）
└── data/                   # 数据目录（本地，不上传）
```

## 技术栈

- **数据库**：DuckDB + SQLAlchemy ORM
- **数据源**：Tushare Pro API
- **回测引擎**：Backtrader + 自定义算子系统
- **实盘对接**：QMT（xtquant，仅 Windows）via REST API
- **Web 服务**：Python stdlib `http.server` + Bokeh 交互图表

## 详细文档

- `docs/DEVELOPMENT.md` — 完整开发文档（架构、模块详解、Web 服务、部署）
- `docs/项目计划.md` — 项目规划和任务清单
