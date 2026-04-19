# 助理智能体架构升级计划 v2：借鉴优秀项目的设计思想

> 前置研究：Claude Code、OpenClaw、Hermes Agent 三大 Agent 框架的架构分析

---

## 第一部分：优秀项目架构研究报告

### 1. Claude Code（Anthropic）— 分层治理架构

**核心设计理念**：Agent 的强大行为不是来自提示词修饰，而是来自**系统属性**——工具可被拒绝、子智能体拥有独立上下文、Hooks 可拦截动作、沙箱可在 OS 层面阻断子进程。

| 层级 | 控制什么 | 加载/执行什么 | 为什么重要 |
|------|---------|--------------|-----------|
| **Agent Loop** | 任务分解和下一步选择 | 工具调用、文件读取、Shell 命令、重试 | 模型从文本生成转向行动的临界点 |
| **Context & Memory** | Claude 当前知道什么、跨会话记住什么 | 对话历史、CLAUDE.md、自动记忆、工具输出、Skills、MCP 工具名 | 大多数"Agent 走神"问题本质上是上下文问题 |
| **Execution Surface** | 工作如何触及代码和系统 | Read、Edit、Bash、WebFetch、子智能体、worktrees、checkpoints | 决定爆炸半径和可复现性 |
| **Governance & Safety** | Claude 被允许尝试什么 | 权限模式、允许/拒绝规则、Hooks、沙箱、信任验证 | 生产环境的真正控制平面 |
| **Extensibility** | 新能力如何接入 | Skills、Plugins、MCP Servers、MCP Prompts、Agent SDK | 灵活性和供应链风险同时增加的地方 |

**关键设计模式**：
- **工具即治理词汇表**：权限规则、子智能体允许列表、Hook 匹配器都引用工具名。MCP 工具统一命名为 `mcp__<server>__<tool>`。
- **Diffs-first 工作流**：颜色化 diff 使变更立即可见，鼓励最小修改，天然支持 TDD。
- **上下文压缩（Compressor）**：当接近上下文限制时总结对话，而非截断。
- **Hooks 拦截**：`PreToolUse`（工具执行前拦截）、`PermissionRequest`（权限申请）、`PostToolUse`（执行后审计）。
- **子智能体隔离**：每个子智能体获得独立的上下文窗口，用于并行工作流。

---

### 2. OpenClaw — Gateway + 人格驱动架构

**核心设计理念**：以**Gateway**为中央控制平面，以**SOUL.md**为 Agent 人格的单一真相源，以**纯 Markdown**为全部配置格式（人类可读写）。

| 组件 | 职责 | 技术实现 |
|------|------|---------|
| **Gateway** | 常驻守护进程，管理会话、路由、工具执行、状态编排 | WebSocket @ 127.0.0.1:18789 |
| **SOUL.md** | Agent 人格配置：个性、价值观、沟通风格 | Markdown + YAML frontmatter |
| **Skills** | 模块化能力，每个 Skill 是包含 SKILL.md 的目录 | YAML frontmatter + 自然语言指令 |
| **Pi Agent Runtime** | ReAct Loop（Reason + Act）执行引擎 | TypeScript, LLM APIs |
| **ClawHub** | 技能市场，社区共享 Skills | 44000+ entries |

**四层架构**：
```
Gateway（控制平面）→ Agent（AI 大脑/LLM 编排）→ Memory（持久存储）→ Skills（模块化能力）
```

**记忆分层**：
- **Daily Logs**（短期）：追加式 Markdown 文件，当前会话记录
- **MEMORY.md**（长期）：用户偏好、重要事实
- **SOUL.md**（人格）：Agent 个性与风格
- **QMD**（语义）：本地向量数据库（v2026.2.2+）

**心跳机制**：Cron 调度器实现" proactive "模式——Agent 可自主监控系统、读取邮件、执行后台任务。

---

### 3. Hermes Agent（Nous Research）— 自改进循环架构

**核心设计理念**：唯一的内置学习循环 Agent——从经验创建技能、在使用过程中改进、主动将知识持久化、搜索自己的历史对话、构建跨会话的用户画像。

| 子系统 | 能力 | 实现 |
|--------|------|------|
| **40+ 工具** | 组织为可组合工具集（web/terminal/file/browser/vision/skills/memory/delegation/cron）| JSON function calling |
| **三层记忆** | 上下文压缩 → SQLite FTS5 会话搜索 → 持久 MEMORY.md | SQLite + Markdown |
| **自主技能创建** | 完成复杂任务后自动评估是否保存为可复用 Skill | Agent 自我管理 |
| **子智能体委托** | 隔离的子智能体用于并行工作流 | 独立上下文 + 工具集 |
| **IterationBudget** | 控制每个任务的最大工具调用次数，防止无限循环 | 可配置预算 |
| **五种终端后端** | local / Docker / SSH / Singularity / Modal | 安全沙箱 |
| **用户建模** | Honcho 辩证推理，跨会话用户画像 | 结构化用户档案 |
| **自修改** | Agent 可读取和重写自己的系统提示词 | 元学习能力 |
| **心跳维护** | 每 6 小时：审查技能、清理输出、整合记忆、写入状态文件 | 定时触发器 |

**三种 API 模式**：
- `chat_completions` — 通用 OpenAI 兼容
- `codex_responses` — OpenAI Codex Responses API
- `anthropic_messages` — Anthropic Messages API（支持提示词缓存）

---

## 第二部分：架构设计启示（可复用的设计模式）

### 模式 A：分层架构（来自 Claude Code）

不要构建"单一大提示词"的聊天机器人。将系统分为清晰的层次，每层有明确的职责边界。

```
┌─────────────────────────────────────────┐
│  Extensibility  │ Skills / Plugins / MCP │
├─────────────────────────────────────────┤
│  Governance     │ Permissions / Hooks    │
├─────────────────────────────────────────┤
│  Execution      │ Tools / Sub-agents     │
├─────────────────────────────────────────┤
│  Context        │ Memory / RAG / Session │
├─────────────────────────────────────────┤
│  Agent Loop     │ Reason → Plan → Act    │
└─────────────────────────────────────────┘
```

### 模式 B：工具即能力的唯一入口（来自 Claude Code + Hermes）

所有 Agent 能力（包括记忆访问、子智能体创建）都通过工具接口暴露。不通过提示词"告诉"Agent 它能做什么，而是通过工具 Schema 让它"发现"自己能做什么。

好处：
- 权限控制天然精确到工具粒度
- 新能力接入不需要改提示词
- 工具调用日志 = 完整的审计追踪

### 模式 C：记忆分层（来自 Hermes + OpenClaw）

| 层级 | 存储 | 生命周期 | 用途 |
|------|------|---------|------|
| **工作记忆** | 上下文窗口 | 当前对话 | LLM 直接可见的上下文 |
| **会话记忆** | SQLite | 单次会话 | 工具输出缓存、中间结果 |
| **长期记忆** | Markdown/DB | 跨会话 | 用户偏好、投资习惯、重要结论 |
| **语义记忆** | 向量数据库 | 永久 | 历史对话语义检索、知识库 |

### 模式 D：技能即文件（来自 OpenClaw）

每个 Skill 是一个目录，包含：
- `SKILL.md` — 技能描述、使用场景、输入输出格式
- `tools/` — 该技能包含的工具实现
- `examples/` — 使用示例

好处：Agent 可以"发现"技能、"学习"技能、甚至"创建"技能。

### 模式 E：迭代预算（来自 Hermes）

每个任务分配 `IterationBudget`，限制最大工具调用次数。防止：
- 无限循环（Agent 在两个工具间反复调用）
- 上下文爆炸（单次对话 token 超限）
- 资源耗尽（长时间占用 LLM API）

### 模式 F：Gateway 控制平面（来自 OpenClaw）

单一入口（Gateway）管理：
- 会话生命周期
- 工具注册与路由
- 事件总线（Event Bus）
- 状态编排

避免每个组件直接调用 LLM，而是通过 Gateway 统一调度。

---

## 第三部分：基于研究的本项目 Agent 架构设计

### 3.1 当前架构问题诊断

当前 `Assistant.vue` 中的 Agent 逻辑：

```
用户输入 → callAPIStream() → LLM 返回 → 是工具调用?
  → 是：前端执行工具 → 结果回填 → 再次调用 LLM
  → 否：speak() 朗读最终回答
```

**问题**：
1. **单层架构**：前端组件同时承担 UI、Agent Loop、工具执行、状态管理
2. **无记忆层**：`apiMessages` 仅存于内存，刷新丢失
3. **工具孤岛**：3 个前端工具无法访问 PostgreSQL 金融数据库
4. **无治理层**：工具调用无权限控制、无审计日志、无迭代限制
5. **无扩展层**：新增工具需要修改 `Assistant.vue`

### 3.2 目标架构：五层 Agent 系统

借鉴 Claude Code 的分层思想，结合 OpenClaw 的 Gateway 模式和 Hermes 的自改进循环：

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 5: Extensibility（扩展层）                            │
│  • Skill Registry（技能注册表）                              │
│  • MCP-compatible Tool Server（MCP 兼容工具服务）           │
│  • 未来：第三方技能接入                                      │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Governance（治理层）                               │
│  • Tool Allow/Deny Rules（工具白名单/黑名单）               │
│  • PreToolUse Hooks（工具调用前拦截）                       │
│  • IterationBudget（迭代预算控制）                          │
│  • Audit Log（审计日志）                                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Execution（执行层）                                │
│  • Tool Router（工具路由）                                  │
│  • Tool Sandbox（工具沙箱）                                 │
│  • Sub-agent Spawner（子智能体创建器）                      │
│  • 金融工具集：query_sql / screen_stocks / run_backtest    │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Context & Memory（上下文与记忆层）                 │
│  • Session Manager（会话管理）                              │
│  • Memory Store（记忆存储：SQLite + Markdown）              │
│  • Semantic Search（语义搜索：向量数据库）                  │
│  • Context Builder（上下文构建器）                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Agent Loop（智能体循环层）                         │
│  • Planner（计划器：ReAct / Plan-and-Solve）                │
│  • Executor（执行器）                                       │
│  • Reflector（反思器）                                      │
│  • SSE Streamer（SSE 流式输出）                            │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 各层详细设计

#### Layer 1: Agent Loop（后端实现，Flask）

**职责**：接收用户输入，运行 Reason → Plan → Act → Observe 循环，SSE 流式返回结果。

**借鉴 Hermes 的三种模式支持**：
- **Direct Mode**：简单问答，直接回复（无需工具）
- **Function Calling Mode**：单步工具调用（查询股价、计算）
- **ReAct Mode**：多步复杂任务（筛选股票 → 回测 → 生成图表）

**关键组件**：
```python
class AgentLoop:
    def __init__(self, session_id, budget=10):
        self.session = SessionManager.get(session_id)
        self.budget = IterationBudget(budget)
        self.planner = Planner()
        self.executor = ToolExecutor()
        self.reflector = Reflector()
    
    async def run(self, user_input):
        # 1. 构建上下文（注入记忆 + 技能描述 + 工具 Schema）
        context = self.build_context(user_input)
        
        # 2. 计划（复杂任务先出计划）
        plan = self.planner.plan(context) if self.is_complex(user_input) else None
        
        # 3. 执行循环
        while not self.budget.is_exhausted():
            response = await self.llm.chat(context)
            
            if response.has_tool_call:
                tool_call = response.tool_call
                # 治理层检查
                if not self.governance.allow(tool_call):
                    yield ToolDeniedEvent(tool_call)
                    continue
                
                result = await self.executor.execute(tool_call)
                yield ToolResultEvent(tool_call, result)
                context.add_tool_result(tool_call, result)
            else:
                # 最终回答
                yield FinalAnswerEvent(response.content)
                break
        
        # 4. 反思（保存经验到记忆）
        self.reflector.reflect(context)
```

#### Layer 2: Context & Memory

**会话管理（借鉴 Claude Code 的 Session 概念）**：
```python
# 数据模型
class ConversationSession:
    id: str
    title: str           # 自动生成或用户命名
    created_at: datetime
    updated_at: datetime
    messages: List[Message]
    metadata: dict       # 关联的股票、策略等

class Message:
    id: str
    role: str            # user / assistant / tool
    content: str
    tool_calls: List[ToolCall]
    created_at: datetime
```

**记忆分层（借鉴 Hermes 三层记忆）**：
```
工作记忆（上下文窗口） ← 从以下构建：
  ├── 当前会话最近 N 条消息
  ├── 相关历史会话（语义搜索召回）
  ├── user_memory.md（用户画像：投资偏好、关注标的、风格）
  └── 技能描述（当前加载的技能）

会话记忆（SQLite）
  ├── conversation_sessions 表
  ├── conversation_messages 表
  └── tool_execution_logs 表（审计追踪）

长期记忆（Markdown 文件）
  ├── user_memory.md — 用户偏好、关注股票、常用分析维度
  ├── investment_notes.md — 重要投资结论、经验教训
  └── 未来：agent_memory.md — Agent 自我改进记录

语义记忆（SQLite FTS5 / 未来 pgvector）
  └── 历史对话全文索引，支持自然语言检索
```

**记忆注入机制**：
每次对话前，自动将 `user_memory.md` 内容注入 system prompt：
```
你是助理小姐，一位专业的量化投研助手。以下是关于用户的已知信息：
---
[用户记忆内容]
---
请根据以上信息提供个性化的投研服务。
```

#### Layer 3: Execution（工具执行层）

**工具注册表（借鉴 Claude Code 的工具命名空间）**：
```python
# 所有工具统一注册
class ToolRegistry:
    def __init__(self):
        self.tools = {}
    
    def register(self, tool: Tool):
        self.tools[tool.name] = tool
    
    def get_schema(self):
        return [t.schema for t in self.tools.values()]

# 金融工具集（核心 — 解决当前最大瓶颈）
tools.register(SQLQueryTool())        # 自然语言/SQL 查询金融数据
tools.register(StockScreenerTool())   # 多因子选股
tools.register(BacktestTool())        # 策略回测
tools.register(ValuationTool())       # 估值分析 PE/PB 分位
tools.register(IndustryAnalysisTool()) # 行业对比
tools.register(ChartGeneratorTool())  # 生成图表（matplotlib/plotly）
tools.register(DataDownloadTool())    # 触发数据下载

# 通用工具集
tools.register(TimeTool())
tools.register(CalculatorTool())
tools.register(WebSearchTool())       # 未来：网络搜索
```

**SQL 查询工具设计（安全优先）**：
```python
class SQLQueryTool(Tool):
    name = "query_financial_data"
    description = "查询金融数据库，支持股票行情、财务指标、行业数据等"
    
    # 只读查询，禁止 DDL/DML
    ALLOWED_PREFIXES = ["SELECT", "WITH", "EXPLAIN"]
    
    async def execute(self, query: str, params: dict = None):
        # 1. 语法检查
        if not any(query.strip().upper().startswith(p) for p in self.ALLOWED_PREFIXES):
            return {"error": "只允许 SELECT 查询"}
        
        # 2. 在沙箱连接上执行（只读权限）
        with get_readonly_engine() as engine:
            df = pd.read_sql(query, engine, params=params)
        
        # 3. 结果格式化（限制行数，防止上下文爆炸）
        return {
            "columns": df.columns.tolist(),
            "data": df.head(50).to_dict("records"),
            "total_rows": len(df),
            "truncated": len(df) > 50
        }
```

#### Layer 4: Governance（治理层）

**迭代预算（借鉴 Hermes）**：
```python
class IterationBudget:
    def __init__(self, max_iterations=10):
        self.max = max_iterations
        self.used = 0
    
    def consume(self):
        self.used += 1
        if self.used >= self.max:
            raise BudgetExhaustedError(f"达到最大迭代次数 {self.max}")
```

**工具权限控制**：
```python
class Governance:
    def __init__(self):
        self.allowed_tools = ["*"]  # 默认允许全部
        self.denied_tools = ["execute_shell", "delete_data"]  # 禁止危险操作
    
    def allow(self, tool_call: ToolCall) -> bool:
        name = tool_call.name
        if name in self.denied_tools:
            return False
        if "*" in self.allowed_tools or name in self.allowed_tools:
            return True
        return False
```

**审计日志**：
```python
class AuditLogger:
    def log_tool_call(self, session_id, tool_call, result, duration_ms):
        # 写入 SQLite tool_execution_logs 表
        pass
```

#### Layer 5: Extensibility（扩展层）

**技能注册表（借鉴 OpenClaw 的 Skill 系统）**：
```python
class Skill:
    name: str
    description: str
    tools: List[Tool]
    examples: List[str]

# 金融分析技能
financial_skill = Skill(
    name="financial_analysis",
    description="财务分析和估值能力",
    tools=[SQLQueryTool, ValuationTool, IndustryAnalysisTool],
    examples=[
        "分析贵州茅台过去 5 年的 ROE 走势",
        "对比银行和保险行业的市盈率"
    ]
)

# 回测技能
backtest_skill = Skill(
    name="strategy_backtest",
    description="策略回测和绩效分析",
    tools=[BacktestTool, ChartGeneratorTool],
    examples=["回测双均线交叉策略在沪深 300 上的表现"]
)
```

**未来 MCP 兼容性**：
将工具封装为 MCP Server，支持外部客户端（Claude Desktop、Cursor）接入。

### 3.4 前后端职责划分

| 职责 | 前端（Vue 3） | 后端（Flask） |
|------|-------------|--------------|
| **Agent Loop** | ❌ 不再承担 | ✅ 统一在 Flask 实现 |
| **工具执行** | ❌ 迁移到后端 | ✅ ToolExecutor |
| **记忆存储** | ❌ 仅读取展示 | ✅ SQLite + Markdown |
| **LLM 调用** | ❌ 代理到后端 | ✅ 统一路由（支持多 provider） |
| **UI 展示** | ✅ 聊天界面、3D 形象、语音 | ❌ |
| **会话管理 UI** | ✅ 列表、新建、切换、搜索 | ✅ CRUD API |
| **语音输出** | ✅ Edge TTS + 口型同步 | ✅ TTS 代理 |
| **语音输入** | ✅ SpeechRecognition | ❌ |

### 3.5 数据流重新设计

```
用户输入
  │
  ▼
┌─────────────────┐
│ 前端: 发送消息   │──POST /api/agent/chat──┐
└─────────────────┘                        │
                                           ▼
                              ┌────────────────────────┐
                              │ Layer 2: 构建上下文     │
                              │ • 加载会话历史          │
                              │ • 注入用户记忆          │
                              │ • 加载技能描述          │
                              └────────────────────────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │ Layer 1: Agent Loop    │
                              │ • 计划（如复杂任务）    │
                              │ • 循环: LLM → 工具?    │
                              │   → 执行 → 观察        │
                              │ • 迭代预算控制          │
                              └────────────────────────┘
                                           │
                              ┌────────────┴────────────┐
                              │                         │
                              ▼                         ▼
                    ┌─────────────────┐      ┌─────────────────┐
                    │ 是工具调用        │      │ 是最终回答       │
                    │ • 治理层检查     │      │ • 保存到会话     │
                    │ • 执行工具       │      │ • SSE 返回文本   │
                    │ • 记录审计日志   │      │ • 触发 TTS      │
                    │ • SSE 返回结果   │      │ • 更新记忆(可选) │
                    └─────────────────┘      └─────────────────┘
                              │                         │
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │ SSE 流式响应到前端       │
                              │ • plan: 计划展示        │
                              │ • tool_call: 工具调用   │
                              │ • tool_result: 结果     │
                              │ • final: 最终回答       │
                              └────────────────────────┘
                                           │
                                           ▼
┌─────────────────┐              ┌────────────────────────┐
│ 前端: 渲染消息   │◄─────────────│ 按 event type 渲染      │
│ • Markdown 文本  │              │ • 计划 → 进度条         │
│ • 工具调用卡片   │              │ • 工具 → 可折叠卡片     │
│ • 图表 inline   │              │ • 图表 → <img>          │
│ • 语音播放      │              │ • 文本 → Markdown       │
└─────────────────┘              └────────────────────────┘
```

### 3.6 SSE 事件协议设计

```json
// 计划事件
{"type": "plan", "content": ["1. 查询符合条件的股票", "2. 获取财务指标", "3. 生成对比图表"]}

// 工具调用事件
{"type": "tool_call", "name": "query_financial_data", "arguments": {"query": "SELECT ..."}}

// 工具结果事件
{"type": "tool_result", "name": "query_financial_data", "result": {...}}

// 思考过程（可选， reasoning 模型）
{"type": "thought", "content": "用户想要筛选高 ROE 低估值的股票..."}

// 最终回答
{"type": "final", "content": "根据查询结果，以下 10 只股票符合您的条件..."}

// 错误事件
{"type": "error", "message": "SQL 查询超时"}
```

---

## 第四部分：实施路径

### Phase 1：Agent 骨架（基础设施，3-4 周）

目标：**Agent Loop 后端化 + 记忆系统 + 核心金融工具**

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 1.1 数据库设计 | `conversation_sessions`、`conversation_messages`、`tool_logs` 表 | P0 |
| 1.2 后端 Agent Loop | Flask Blueprint `/api/agent/*`，实现 ReAct 循环 | P0 |
| 1.3 会话管理 API | CRUD 接口 + 前端会话列表 UI | P0 |
| 1.4 记忆系统 | SQLite 存储 + `user_memory.md` 自动注入 | P0 |
| 1.5 工具迁移 | 前端 3 工具迁移到后端 + 新增 `query_financial_data` | P0 |
| 1.6 治理层 | IterationBudget + 工具权限 + 审计日志 | P1 |
| 1.7 SSE 协议 | 统一 SSE 事件类型，前端按 type 渲染 | P0 |

### Phase 2：能力扩展（工具生态，2-3 周）

目标：**金融工具集完善 + 可视化 + 自主工作流**

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 2.1 选股工具 | `screen_stocks`（ROE/PE/增速组合筛选） | P0 |
| 2.2 估值工具 | `get_stock_valuation`（PE/PB 历史分位） | P0 |
| 2.3 回测工具 | `run_backtest`（调用 engine/backtest） | P0 |
| 2.4 图表工具 | `generate_chart`（matplotlib → base64） | P1 |
| 2.5 计划器 | 复杂任务自动分解为步骤清单 | P1 |
| 2.6 反思器 | 任务完成后自动总结、更新记忆 | P1 |
| 2.7 语音输入 | Web Speech API SpeechRecognition | P1 |

### Phase 3：智能化（高级功能，2-3 周）

目标：**RAG + 自主改进 + MCP**

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 3.1 RAG 知识库 | ChromaDB/pgvector + 文档上传 | P2 |
| 3.2 语义搜索 | 历史对话 FTS5 索引 | P1 |
| 3.3 技能系统 | Skill Registry + 技能发现 | P2 |
| 3.4 后台任务 | 定时任务 + 系统通知 | P2 |
| 3.5 MCP 兼容 | 工具封装为 MCP Server | P2 |
| 3.6 多模态 | 图片上传分析（需要多模态 LLM） | P3 |

---

## 第五部分：关键设计决策

### 决策 1：Agent Loop 放在前端还是后端？

**决定：全部迁移到后端。**

理由：
- 工具需要访问 PostgreSQL（金融数据在后端）
- 记忆需要持久化（SQLite 在后端）
- 治理需要统一控制（权限、预算、审计）
- 未来支持多客户端（Web、移动端共享同一 Agent 后端）

### 决策 2：记忆存储选 SQLite 还是 PostgreSQL？

**决定：会话记忆用 SQLite，金融数据保持 PostgreSQL。**

理由：
- 对话历史是用户私有的、单机的（Electron 桌面端场景），不需要共享
- SQLite 零配置、无需额外服务、随 Electron 打包即可
- 金融数据已在 PostgreSQL，通过 SQLAlchemy 只读连接查询

### 决策 3：工具调用模式选 Function Calling 还是 ReAct？

**决定：两者结合，按任务复杂度自动选择。**

- **Direct Mode**：简单问答（"你好" / "现在几点"）→ 直接回复
- **Function Calling Mode**：单步数据查询（"查一下茅台的股价"）→ 调用一次工具
- **ReAct Mode**：复杂多步任务（"筛选高 ROE 低估值股票并回测"）→ 计划 + 多步执行 + 反思

### 决策 4：技能系统采用文件还是数据库？

**决定：文件优先（SKILL.md），数据库索引。**

理由：
- 借鉴 OpenClaw，纯 Markdown 配置人类可读写
- 项目已有 `SKILL.md` 文化（根目录已有 `SKILL.md`）
- 数据库仅存储技能注册信息（名称、路径、启用状态）

---

## 第六部分：总结

当前助理已完成：
- ✅ **好看的皮囊**：3D VRM 虚拟形象 + Edge TTS 语音 + 实时口型同步
- ✅ **流畅的对话**：SSE 流式响应 + Markdown 渲染

通过借鉴三大优秀项目的架构设计，下一步将构建：
- 🏗️ **Agent Loop 后端化**：五层架构（Loop → Context → Execution → Governance → Extensibility）
- 🏗️ **记忆分层系统**：工作记忆 + 会话记忆 + 长期记忆 + 语义记忆
- 🏗️ **金融工具生态**：SQL 查询、选股、估值、回测、图表生成
- 🏗️ **治理与预算**：权限控制、迭代预算、审计日志
- 🏗️ **技能系统**：可扩展的 Skill Registry

**最重要的三个改进**：
1. **Agent Loop 后端化** — 从"前端聊天组件"升级为"后端 Agent 服务"
2. **金融数据库接入** — 让 Agent 能查数据、能选股、能回测
3. **持久化记忆** — 让 Agent 记住用户、记住对话、记住经验

这三项完成后，助理将从"带虚拟形象的聊天机器人"进化为真正的"量化投研 Agent"。
