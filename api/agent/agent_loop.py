"""
Agent ReAct 循环

流程：
  用户消息 → 持久化 → 加载上下文（带 Token 预算裁剪）→ LLM 流式调用
    → 有工具调用? → 参数校验 → 执行（带超时）→ 观察 → 继续循环
    → 无工具调用? → 持久化 assistant 消息 → yield final → 结束

全部使用 requests(stream=True) 同步实现，适配 Flask threaded 模式。
"""
import json
from pathlib import Path
from typing import Generator

import requests
from loguru import logger

from api.agent.adapters import get_adapter
from api.agent.budget import BudgetExhaustedError, IterationBudget, TokenBudget
from api.agent.db import AgentDB
from api.agent.tool_registry import ToolRegistry

_MEMORY_PATH = Path(__file__).parent.parent.parent / "data" / "user_memory.md"

# 上下文保留的 token 上限（粗估）
_CTX_TOKEN_LIMIT = 8_000


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


# ── Token 估算 ────────────────────────────────────────────────────────────────

def _estimate_tokens(text: str) -> int:
    """
    粗略估算 token 数（无需 tiktoken）。
    中文字符 ≈ 0.7 token/字，英文/符号 ≈ 0.25 token/字符。
    """
    if not text:
        return 0
    chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other = len(text) - chinese
    return int(chinese * 0.7 + other * 0.25) + 1


def _trim_messages(messages: list[dict], max_tokens: int = _CTX_TOKEN_LIMIT) -> list[dict]:
    """
    从最新消息向前保留，直到超过 max_tokens 为止。
    保证至少保留最后 6 条（防止极端情况下上下文为空）。
    """
    if len(messages) <= 6:
        return messages

    total = 0
    keep_from = 0  # 默认不裁剪，仅在超出 token 上限时更新
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        content_tokens = _estimate_tokens(msg.get("content") or "")
        tc_tokens = _estimate_tokens(
            json.dumps(msg["tool_calls"], ensure_ascii=False) if msg.get("tool_calls") else ""
        )
        total += content_tokens + tc_tokens
        if total > max_tokens:
            # min：确保 keep_from 不超过 len-6，即至少保留最后 6 条
            keep_from = min(i + 1, len(messages) - 6)
            break

    if keep_from > 0:
        logger.debug(f"上下文裁剪：丢弃 {keep_from} 条旧消息，保留 {len(messages) - keep_from} 条，"
                     f"估计 {total} tokens")
    return messages[keep_from:]


# ── 记忆注入 ──────────────────────────────────────────────────────────────────

def _load_user_memory() -> str:
    if _MEMORY_PATH.exists():
        try:
            return _MEMORY_PATH.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return ""


def _build_system_prompt(base_system: str) -> str:
    memory = _load_user_memory()
    if memory:
        return (
            base_system.rstrip()
            + "\n\n以下是关于用户的已知信息，请据此提供个性化服务：\n---\n"
            + memory
            + "\n---"
        )
    return base_system


def _messages_to_api_format(messages: list[dict]) -> list[dict]:
    """将 DB 格式消息转为 LLM API 消息格式"""
    result = []
    for m in messages:
        role = m["role"]
        content = m.get("content") or ""
        tool_calls = m.get("tool_calls")
        tool_call_id = m.get("tool_call_id")

        if role == "tool":
            result.append({
                "role": "tool",
                "tool_call_id": tool_call_id or "",
                "content": content,
            })
        elif role == "assistant" and tool_calls:
            msg: dict = {"role": "assistant", "content": content}
            msg["tool_calls"] = tool_calls
            result.append(msg)
        else:
            result.append({"role": role, "content": content})
    return result


# ── AgentLoop ─────────────────────────────────────────────────────────────────

class AgentLoop:
    def __init__(self, registry: ToolRegistry, db: AgentDB):
        self.registry = registry
        self.db = db

    def run(
        self,
        session_id: str,
        user_message: str,
        provider: str,
        api_key: str,
        api_url: str,
        model: str,
        system_prompt: str,
        max_iterations: int = 10,
        max_tokens: int = 80_000,
    ) -> Generator[str, None, None]:
        """主 ReAct 循环，yield SSE 字符串（data: {...}\\n\\n）"""

        # 1. 持久化用户消息
        self.db.add_message(session_id, "user", user_message)

        # 自动生成会话标题
        session = self.db.get_session(session_id)
        if session and not session.get("title"):
            title = user_message[:30].replace("\n", " ")
            self.db.update_session_title(session_id, title)
            yield _sse({"type": "session", "session_id": session_id, "title": title})
        else:
            yield _sse({"type": "session", "session_id": session_id,
                        "title": (session or {}).get("title", "")})

        # 2. 准备上下文
        system = _build_system_prompt(system_prompt)
        adapter = get_adapter(provider)
        tools = self.registry.all_definitions()
        budget = IterationBudget(max_iterations)
        token_budget = TokenBudget(max_tokens)

        try:
            yield from self._react_loop(
                session_id, adapter, api_key, api_url, model,
                system, tools, budget, token_budget,
            )
        except BudgetExhaustedError as e:
            yield _sse({"type": "budget_exceeded", "iterations": budget.used,
                        "message": str(e)})
        except Exception as e:
            logger.exception(f"Agent loop 异常: {e}")
            yield _sse({"type": "error", "code": "agent_error", "message": str(e)})

        yield _sse({"type": "done"})

    def _react_loop(
        self,
        session_id: str,
        adapter,
        api_key: str,
        api_url: str,
        model: str,
        system: str,
        tools: list,
        budget: IterationBudget,
        token_budget: TokenBudget,
    ) -> Generator[str, None, None]:

        while True:
            # ── 加载并裁剪上下文 ──────────────────────────────
            db_messages = self.db.get_messages(session_id, limit=80)
            trimmed = _trim_messages(db_messages)
            api_messages = _messages_to_api_format(trimmed)

            payload = adapter.build_request(api_messages, tools, system, model, stream=True)
            url = adapter.get_url(api_url)
            headers = adapter.get_headers(api_key)

            # ── 调用 LLM ──────────────────────────────────────
            try:
                resp = requests.post(url, json=payload, headers=headers,
                                     stream=True, timeout=120)
                resp.raise_for_status()
            except requests.HTTPError as e:
                body = ""
                try:
                    body = e.response.text[:500]
                except Exception:
                    pass
                yield _sse({"type": "error", "code": "api_error",
                            "message": f"HTTP {e.response.status_code}: {body}"})
                return
            except requests.RequestException as e:
                yield _sse({"type": "error", "code": "network_error", "message": str(e)})
                return

            # ── 解析流式响应 ──────────────────────────────────
            accumulated_text = ""
            final_tool_calls: list[dict] = []
            got_finish = False  # 是否收到了明确的结束信号

            for chunk in adapter.iter_chunks(resp):
                if chunk.text:
                    accumulated_text += chunk.text
                    token_budget.charge(chunk.text)
                    yield _sse({"type": "thought", "content": chunk.text})

                if chunk.tool_calls:
                    final_tool_calls = chunk.tool_calls

                if chunk.finish_reason == "stop":
                    got_finish = True
                    self.db.add_message(session_id, "assistant", accumulated_text)
                    yield _sse({"type": "final", "content": accumulated_text})
                    return

                if chunk.finish_reason == "tool_calls":
                    got_finish = True
                    break

                # Token 预算检查
                if token_budget.is_exhausted():
                    yield _sse({"type": "budget_exceeded",
                                "code": "token_budget",
                                "message": f"Token 预算已耗尽（{token_budget.used}/{token_budget.max}）"})
                    return

            # ── Bug 2 修复：流结束但未收到 finish 信号 ────────
            if not got_finish and not final_tool_calls:
                # 流异常结束（网络截断等），用当前累积内容作为最终回复
                logger.warning(f"流提前结束，未收到 finish_reason，累积文本长度={len(accumulated_text)}")
                self.db.add_message(session_id, "assistant", accumulated_text)
                # 无论是否有内容，都必须发 final，防止前端永久 loading
                yield _sse({"type": "final", "content": accumulated_text})
                return

            if not final_tool_calls:
                # 有 accumulated_text 但 finish 未明确（部分 provider 不发 finish）
                self.db.add_message(session_id, "assistant", accumulated_text)
                yield _sse({"type": "final", "content": accumulated_text})
                return

            # ── 3. 持久化 assistant 消息（含 tool_calls）────────
            self.db.add_message(
                session_id, "assistant",
                accumulated_text or None,
                tool_calls=final_tool_calls,
            )

            # ── 4. 执行工具 ──────────────────────────────────────
            for tc in final_tool_calls:
                fn = tc.get("function", {})
                tool_name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")
                tc_id = tc.get("id", "")

                # Bug 1 修复：参数 JSON 解析失败时发错误事件，不静默传空字典
                try:
                    args = json.loads(raw_args) if raw_args else {}
                except json.JSONDecodeError as e:
                    err_msg = f"工具 {tool_name} 参数 JSON 解析失败: {e}"
                    logger.warning(f"{err_msg}，raw={raw_args!r}")
                    yield _sse({"type": "tool_call", "id": tc_id,
                                "name": tool_name, "arguments": {}})
                    yield _sse({"type": "tool_result", "id": tc_id,
                                "name": tool_name,
                                "result": f"[参数错误] {err_msg}"})
                    self.db.add_message(
                        session_id, "tool",
                        f"[参数错误] {err_msg}",
                        tool_call_id=tc_id,
                    )
                    self.db.append_audit(session_id, "tool_arg_error", tool_name,
                                        {"raw_args": raw_args, "error": str(e)})
                    continue  # 跳过此工具，继续下一个

                yield _sse({"type": "tool_call", "id": tc_id,
                            "name": tool_name, "arguments": args})

                # 执行工具（registry 内部已有超时控制）
                result = self.registry.execute(tool_name, args)
                token_budget.charge(result)

                self.db.append_audit(session_id, "tool_call", tool_name,
                                     {"id": tc_id, "args": args, "result": result[:500]})

                yield _sse({"type": "tool_result", "id": tc_id,
                            "name": tool_name, "result": result})

                self.db.add_message(
                    session_id, "tool", result, tool_call_id=tc_id
                )

            # ── 5. 迭代预算检查 ───────────────────────────────
            budget.tick()
            remaining = budget.remaining()
            if remaining <= 2:
                yield _sse({"type": "budget_warning", "remaining": remaining})
