"""
LLM 提供商适配器

内部工具定义统一使用 OpenAI format，
各适配器负责：
  1. build_request() — 将内部格式转换为各 API 的请求 payload
  2. iter_chunks()   — 解析流式响应，yield ChunkResult

支持：
  - openai / kimi / 任何 OpenAI 兼容接口  → OpenAIAdapter
  - anthropic                              → AnthropicAdapter

TODO（阶段3评估）：Kimi Wire 本地模式整合
────────────────────────────────────────────
当前 Kimi Wire 模式（api/handlers/kimi_wire_handler.py）通过子进程
`kimi --wire` 以 JSON-RPC 2.0 over stdin/stdout 协议通信，与现有的
HTTP adapter 架构差异较大：
  - 无 HTTP request/response 对象
  - 使用 initialize/prompt 等 JSON-RPC 方法
  - 响应通过 event 通知（ContentPart / TurnEnd）传递

整合方案对比：
  A) 创建 KimiWireAdapter 实现相同接口 — 需大量包装代码，可读性差
  B) 在 agent_loop.py 中通过策略模式分流 — 改动较小，但架构不统一
  C) 将 /api/assistant/chat 也纳入 AgentLoop — 最佳长期方案，但需将
     KimiWireSession 封装为类似 requests.Response 的流式迭代器

建议：当前前端已通过 useChat.js 统一调用入口，后端双轨并行可接受。
如需统一，优先方案 C：为 KimiWireHandler 添加 iter_chunks() 生成器，
使其行为接近 HTTP 流式响应，然后接入 AgentLoop。
"""
import json
from dataclasses import dataclass, field
from typing import Generator, Iterator


@dataclass
class ChunkResult:
    text: str = ""                        # 增量文本（thought/final）
    tool_calls: list[dict] = field(default_factory=list)  # 完整的 tool call 列表（完成后一次性给出）
    finish_reason: str = ""               # "stop" | "tool_calls" | ""


class OpenAIAdapter:
    """OpenAI / Kimi / 任何 OpenAI 兼容接口"""

    provider_name = "openai"

    def build_request(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: str,
        model: str,
        stream: bool = True,
    ) -> dict:
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)
        payload = {
            "model": model,
            "messages": all_messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return payload

    def get_headers(self, api_key: str) -> dict:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def get_url(self, api_url: str) -> str:
        base = api_url.rstrip("/")
        if not base.endswith("/chat/completions"):
            base += "/chat/completions"
        return base

    def iter_chunks(self, response) -> Generator[ChunkResult, None, None]:
        """解析 OpenAI 格式的 SSE 流，yield ChunkResult"""
        tc_accum: dict[int, dict] = {}  # index → tool call accumulator

        for line in response.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8")
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                # 流结束，如果有工具调用则一次性输出
                if tc_accum:
                    tcs = [tc_accum[i] for i in sorted(tc_accum)]
                    yield ChunkResult(tool_calls=tcs, finish_reason="tool_calls")
                return
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue

            choice = (obj.get("choices") or [{}])[0]
            delta = choice.get("delta", {})
            finish_reason = choice.get("finish_reason") or ""

            # 增量文本
            if delta.get("content"):
                yield ChunkResult(text=delta["content"])

            # 增量工具调用（OpenAI 分块给出）
            for tc_delta in delta.get("tool_calls") or []:
                idx = tc_delta.get("index", 0)
                if idx not in tc_accum:
                    tc_accum[idx] = {
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    }
                acc = tc_accum[idx]
                if tc_delta.get("id"):
                    acc["id"] += tc_delta["id"]
                fn = tc_delta.get("function", {})
                if fn.get("name"):
                    acc["function"]["name"] += fn["name"]
                if fn.get("arguments"):
                    acc["function"]["arguments"] += fn["arguments"]

            if finish_reason == "tool_calls":
                tcs = [tc_accum[i] for i in sorted(tc_accum)]
                yield ChunkResult(tool_calls=tcs, finish_reason="tool_calls")
                tc_accum = {}
            elif finish_reason == "stop":
                yield ChunkResult(finish_reason="stop")


class AnthropicAdapter:
    """Anthropic Messages API"""

    provider_name = "anthropic"

    def build_request(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: str,
        model: str,
        stream: bool = True,
    ) -> dict:
        # Anthropic 不允许 system 在 messages 里
        payload: dict = {
            "model": model,
            "max_tokens": 4096,
            "stream": stream,
            "messages": self._convert_messages(messages),
        }
        if system_prompt:
            payload["system"] = system_prompt
        if tools:
            payload["tools"] = self._convert_tools(tools)
        return payload

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        """将 OpenAI 格式消息转为 Anthropic 格式"""
        result = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                continue  # system 单独处理
            if role == "tool":
                # OpenAI tool result → Anthropic tool_result
                result.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": msg.get("content", ""),
                    }],
                })
            elif role == "assistant" and msg.get("tool_calls"):
                # assistant with tool calls → Anthropic tool_use
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {})
                    try:
                        input_args = json.loads(fn.get("arguments", "{}"))
                    except Exception:
                        input_args = {}
                    content.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": fn.get("name", ""),
                        "input": input_args,
                    })
                result.append({"role": "assistant", "content": content})
            else:
                result.append({"role": role, "content": msg.get("content", "")})
        return result

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """OpenAI tool format → Anthropic tool format"""
        converted = []
        for t in tools:
            fn = t.get("function", {})
            converted.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })
        return converted

    def get_headers(self, api_key: str) -> dict:
        return {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def get_url(self, api_url: str) -> str:
        base = api_url.rstrip("/")
        if not base.endswith("/messages"):
            base += "/messages"
        return base

    def iter_chunks(self, response) -> Generator[ChunkResult, None, None]:
        """
        解析 Anthropic SSE 流，yield ChunkResult。

        Bug 3 修复：
        - message_delta(stop_reason=tool_use) 是权威的结束信号，yield 后清空 tool_uses
        - message_stop 是流的最终清理事件，不再重复 yield tool_calls
        - 若 message_delta 未出现（流截断），在循环结束后做一次补偿 yield
        """
        tool_uses: dict[int, dict] = {}   # index → tool use accumulator
        _tool_calls_emitted = False        # 防止重复 yield tool_calls

        for line in response.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8")
            if line.startswith("event:"):
                continue
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data:
                continue
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue

            event_type = obj.get("type", "")

            if event_type == "content_block_start":
                block = obj.get("content_block", {})
                idx = obj.get("index", 0)
                if block.get("type") == "tool_use":
                    tool_uses[idx] = {
                        "id": block.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": block.get("name", ""),
                            "arguments": "",
                        },
                    }

            elif event_type == "content_block_delta":
                delta = obj.get("delta", {})
                idx = obj.get("index", 0)
                if delta.get("type") == "text_delta":
                    yield ChunkResult(text=delta.get("text", ""))
                elif delta.get("type") == "input_json_delta":
                    if idx in tool_uses:
                        tool_uses[idx]["function"]["arguments"] += delta.get("partial_json", "")

            elif event_type == "message_delta":
                stop_reason = obj.get("delta", {}).get("stop_reason", "")
                if stop_reason == "tool_use" and tool_uses and not _tool_calls_emitted:
                    tcs = [tool_uses[i] for i in sorted(tool_uses)]
                    yield ChunkResult(tool_calls=tcs, finish_reason="tool_calls")
                    _tool_calls_emitted = True
                    tool_uses = {}
                elif stop_reason == "end_turn":
                    yield ChunkResult(finish_reason="stop")

            # message_stop：仅作流结束标记，不再 yield
            # （tool_uses 此时应已通过 message_delta 清空；
            #   若流被截断，在循环结束后的补偿块处理）

        # ── 流结束后补偿：应对流截断导致 message_delta 未到达的情况 ──
        if tool_uses and not _tool_calls_emitted:
            tcs = [tool_uses[i] for i in sorted(tool_uses)]
            yield ChunkResult(tool_calls=tcs, finish_reason="tool_calls")


def get_adapter(provider: str):
    """根据 provider 名称返回对应适配器实例"""
    if provider == "anthropic":
        return AnthropicAdapter()
    return OpenAIAdapter()
