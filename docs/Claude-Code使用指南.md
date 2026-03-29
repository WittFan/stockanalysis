# Claude Code 使用指南

> 本文档面向本项目的日常开发，系统整理 Claude Code 的高效使用方法。

---

## 一、核心原则

**把 Claude Code 当成一个熟悉项目的同事：说人话、给足上下文、及时反馈。**

Claude Code 每次对话会自动加载：
- `CLAUDE.md` — 项目上下文、技术栈、开发约定
- 记忆系统 — 你的偏好、历史决策、关键约束
- `.claude/commands/` — 自定义斜杠命令

这意味着你不需要每次重复介绍项目背景。

---

## 二、提示词技巧

### 2.1 任务描述要具体

| 差 | 好 |
|---|---|
| "重构引擎" | "把 engine.py 中的 PyBroker 替换为 Backtrader Cerebro" |
| "修 bug" | "运行 ETF 回测时 WeightERC 算子报 KeyError，报错信息如下：..." |
| "加个功能" | "在 engine/algos/ 下新增一个动量择时算子，参考 algos_picktime.py 的写法" |

### 2.2 高效提示的结构

```
[做什么] + [在哪里] + [怎么验证]

示例：
"在 datafeed/expr_funcs.py 中添加 rolling_rank 函数，
 签名为 rolling_rank(series, n) -> pd.Series，
 实现后写一个简单测试验证。"
```

### 2.3 给上下文比描述问题更高效

- 贴报错信息的完整 traceback
- 贴相关代码片段
- 截图也可以直接粘贴（Ctrl+V）
- 用 `@文件路径` 直接引用文件

### 2.4 大任务拆步骤

不要一次说"把P0全做了"，而是：
1. "先做阶段一：统一引擎为 Backtrader"
2. 完成后开新对话："继续阶段二：调通 backtrader_qmt_api"

---

## 三、对话管理

### 3.1 一个对话做一件事

Claude Code 的上下文窗口有限，对话越长性能越慢。最佳实践：

- 一个对话完成一个独立任务
- 完成后开新对话做下一件
- 新对话开头点明任务和上次进度

```
"继续 P0 阶段一，上次已完成 Engine 类的 Cerebro 封装，
 现在做数据加载适配：Duckdbloader 输出 → bt.feeds.PandasData"
```

### 3.2 上下文管理命令

| 命令 | 用途 | 何时用 |
|------|------|--------|
| `/compact` | 压缩上下文，保留关键信息 | 对话太长变慢时 |
| `/compact 保留xxx相关内容` | 压缩时指定保留内容 | 有特定上下文要保留时 |
| `/clear` | 清空上下文重新开始 | 切换到完全无关的任务时 |
| `/context` | 查看当前上下文使用量 | 估计还能聊多久 |

### 3.3 会话恢复

```bash
# 命名会话（方便后续恢复）
claude -n "p0-stage1"

# 恢复之前的会话
claude --resume p0-stage1

# 继续最近的对话
claude --continue
```

---

## 四、本项目的自定义命令

在对话中直接输入以下命令即可使用：

| 命令 | 功能 |
|------|------|
| `/bt-test` | 运行 ETF 风险平价策略回测验证 |
| `/pull-data` | 拉取 Tushare 数据 |
| `/check-db` | 检查 DuckDB 数据库状态（表、行数、更新时间） |
| `/new-algo 动量择时 根据MA20判断趋势` | 快速创建新算子 |
| `/plan-status` | 查看项目计划进度，找到下一个要做的任务 |

### 创建新命令

在 `.claude/commands/` 下创建 `.md` 文件即可，格式：

```markdown
描述这个命令要做什么。

步骤：
1. 第一步
2. 第二步
3. ...
```

用 `$ARGUMENTS` 接收参数（如 `/new-algo $ARGUMENTS`）。

---

## 五、记忆系统

### 5.1 让 Claude 记住你的偏好

在对话中说：

```
"记住：测试时不要用 mock，直接连数据库"
"记住：提交代码前先运行回测验证"
"记住：我习惯用 f-string 而不是 format"
```

Claude 会保存到记忆文件，下次对话自动加载。

### 5.2 纠正并固化

当 Claude 做了你不想要的事：

```
"别用 print 调试，用 logger.info，记住这个"
"不要自动加 type hints 到我没改的代码，记住"
```

### 5.3 查看和管理记忆

```
/memory              # 查看所有记忆文件
```

记忆存储在 `~/.claude/projects/<project>/memory/` 下。

---

## 六、权限模式

按 **Shift+Tab** 可在对话中循环切换权限模式。

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **默认模式** | 读文件自动，写文件和命令需确认 | 日常开发 |
| **acceptEdits** | 文件编辑自动，命令需确认 | 批量修改多个文件 |
| **plan** | 只读，不做任何修改 | 调研代码、规划方案 |
| **auto** | 所有操作自动执行 | 信任度高的长任务 |

### 建议的工作方式

1. **探索/规划阶段**：用 plan 模式，安全地读代码、理解架构
2. **编码阶段**：用默认或 acceptEdits 模式
3. **批量修改**：用 acceptEdits 或 auto 模式，省去逐个确认

---

## 七、快捷键

### 核心快捷键

| 快捷键 | 功能 |
|--------|------|
| `Enter` | 提交消息 |
| `Escape` | 取消输入 |
| `Shift+Tab` | 切换权限模式 |
| `Ctrl+C` | 中断当前操作 |
| `Ctrl+R` | 搜索历史对话 |
| `Ctrl+T` | 显示/隐藏任务列表 |
| `Ctrl+V` | 粘贴图片 |
| `Ctrl+G` | 用外部编辑器编写长提示 |
| `Ctrl+_` | 撤销上次操作 |

### 自定义快捷键

编辑 `~/.claude/keybindings.json`：

```json
{
  "bindings": [
    {
      "context": "Chat",
      "bindings": {
        "ctrl+shift+c": "chat:submit"
      }
    }
  ]
}
```

---

## 八、多文件编辑技巧

### 8.1 先规划后执行

```
"我要重构 engine/ 目录，先列出所有需要改的文件和改动方案，不要动手"
```

审核方案后再说："按方案执行"。

### 8.2 用 Worktree 隔离实验

```
"创建一个 worktree 来尝试重构方案"
```

这会在独立分支工作，不影响主分支。失败了可以直接丢弃。

### 8.3 并行开发

在不同终端窗口：

```bash
# 窗口 1：重构引擎
claude --worktree refactor-engine

# 窗口 2：修 bug
claude --worktree fix-datafeed-bug
```

两个会话独立工作，互不影响。

---

## 九、调试技巧

### 9.1 给完整上下文

```
"运行 python ETF-大类资产-风险平价.py 报错：

[粘贴完整 traceback]

帮我修复。"
```

### 9.2 让 Claude 自己复现

```
"这个函数有 bug，先写一个能触发 bug 的测试用例，
 然后修复代码，最后运行测试确认修复。"
```

### 9.3 调试 Claude 本身

如果 Claude 的行为不对：

```
/debug "Claude 一直在尝试用 PyBroker 而不是 Backtrader"
```

---

## 十、Git 工作流

### 10.1 提交代码

```
"查看改动，帮我提交，commit message 用中文"
```

Claude 会自动：查看 diff → 生成 commit message → 提交。

### 10.2 创建 PR

```
"基于当前分支创建 PR 到 main"
```

### 10.3 权限配置（已配置）

本项目 `.claude/settings.local.json` 已允许 git 命令自动执行，无需每次确认。

---

## 十一、进阶功能

### 11.1 Headless 模式（非交互式）

```bash
# 快速问答
claude -p "解释 engine/algos/algo_base.py 的设计模式"

# 管道式使用
claude -p "列出所有算子类名" --output-format json | jq '.result'

# CI/CD 集成
claude --bare -p "检查这次提交是否有安全问题" --allowedTools "Read"
```

### 11.2 Hook 系统

在 `.claude/settings.local.json` 中配置自动化行为：

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "echo '文件已修改' | head -1"
          }
        ]
      }
    ]
  }
}
```

常用场景：
- 编辑文件后自动格式化
- 提交前自动运行测试
- 完成任务后桌面通知

### 11.3 MCP 扩展

通过 MCP 服务器扩展 Claude Code 的能力：

```bash
# 添加 MCP 服务器
claude mcp add <server-name>

# 查看已配置的 MCP
/mcp
```

### 11.4 子代理

当任务需要大量搜索但只需要结果摘要时，Claude 会自动使用子代理，在独立上下文中工作，不污染主对话。

也可以创建自定义子代理，放在 `.claude/agents/` 下。

---

## 十二、常用斜杠命令速查

| 命令 | 功能 |
|------|------|
| `/help` | 帮助信息 |
| `/compact` | 压缩上下文 |
| `/clear` | 清空对话 |
| `/context` | 查看上下文使用量 |
| `/memory` | 管理记忆 |
| `/plan` | 进入规划模式 |
| `/rewind` | 回退到检查点 |
| `/resume` | 恢复之前的会话 |

---

## 十三、高效使用清单

开始新任务前的检查清单：

- [ ] 任务描述是否具体？（文件名、函数名、期望结果）
- [ ] 是否需要拆分成多步？（超过3步考虑拆分）
- [ ] 是否在新对话中开始？（上个任务已完成）
- [ ] 是否需要先规划？（复杂任务用 plan 模式）
- [ ] 验证方式是否明确？（测试、运行、diff）

开发过程中：

- [ ] Claude 做错了？及时纠正并说"记住"
- [ ] 对话变慢了？用 `/compact` 压缩
- [ ] 需要实验？用 worktree 隔离
- [ ] 多文件修改？考虑 acceptEdits 模式
