"""
Agent Blueprint — /api/agent/*

POST /api/agent/chat                         主 Agent 入口（SSE 流式）
GET  /api/agent/sessions                     会话列表
POST /api/agent/sessions                     创建新会话
DELETE /api/agent/sessions/<session_id>      删除会话
GET  /api/agent/sessions/<session_id>/messages  获取消息历史
"""
from flask import Blueprint, Response, jsonify, request, stream_with_context

from api.agent.agent_loop import AgentLoop
from api.agent.db import AgentDB
from api.agent.tool_registry import ToolRegistry


def make_agent_bp(db: AgentDB, registry: ToolRegistry) -> Blueprint:
    bp = Blueprint("agent", __name__)
    loop = AgentLoop(registry=registry, db=db)

    # ── 主 Chat 接口 ─────────────────────────────────────────────────────────

    @bp.post("/agent/chat")
    def chat():
        body = request.get_json(force=True, silent=True) or {}

        # 必填字段
        message = (body.get("message") or "").strip()
        if not message:
            return jsonify({"error": "message 不能为空"}), 400

        provider    = body.get("provider", "openai")
        api_key     = body.get("api_key", "")
        api_url     = body.get("api_url", "https://api.openai.com/v1")
        model       = body.get("model", "gpt-4o-mini")
        system_prompt = body.get("system_prompt", "你是一位专业的量化投研助手，名叫助理小姐，能够分析股票数据、解读财务指标并提供投资建议。")
        max_iter    = int(body.get("max_iterations", 10))

        # 会话 ID（可选，不传则自动创建）
        session_id = body.get("session_id") or None
        if not session_id:
            session_id = db.create_session(provider=provider, model=model)
        elif not db.get_session(session_id):
            # session_id 传了但不存在（可能被删除），重新创建
            session_id = db.create_session(provider=provider, model=model)

        def generate():
            yield from loop.run(
                session_id=session_id,
                user_message=message,
                provider=provider,
                api_key=api_key,
                api_url=api_url,
                model=model,
                system_prompt=system_prompt,
                max_iterations=max_iter,
            )

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # ── 会话管理 ─────────────────────────────────────────────────────────────

    @bp.get("/agent/sessions")
    def list_sessions():
        limit = int(request.args.get("limit", 50))
        sessions = db.list_sessions(limit=limit)
        return jsonify(sessions)

    @bp.post("/agent/sessions")
    def create_session():
        body = request.get_json(force=True, silent=True) or {}
        session_id = db.create_session(
            provider=body.get("provider", ""),
            model=body.get("model", ""),
        )
        return jsonify({"session_id": session_id}), 201

    @bp.delete("/agent/sessions/<session_id>")
    def delete_session(session_id: str):
        if not db.get_session(session_id):
            return jsonify({"error": "会话不存在"}), 404
        db.delete_session(session_id)
        return jsonify({"ok": True})

    @bp.get("/agent/sessions/<session_id>/messages")
    def get_messages(session_id: str):
        if not db.get_session(session_id):
            return jsonify({"error": "会话不存在"}), 404
        limit = int(request.args.get("limit", 60))
        messages = db.get_messages(session_id, limit=limit)
        return jsonify(messages)

    return bp
