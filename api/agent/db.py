"""
Agent 会话持久化层（SQLite）

数据库路径：data/agent.db（与项目 data/ 目录并列）
使用标准库 sqlite3，不依赖 SQLAlchemy。
"""
import json
import sqlite3
import time
import uuid
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'agent.db'

DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    title        TEXT NOT NULL DEFAULT '',
    provider     TEXT NOT NULL DEFAULT '',
    model        TEXT NOT NULL DEFAULT '',
    created_at   INTEGER NOT NULL,
    updated_at   INTEGER NOT NULL,
    message_count INTEGER NOT NULL DEFAULT 0,
    is_archived  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    message_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    role         TEXT NOT NULL,
    content      TEXT,
    tool_calls   TEXT,
    tool_call_id TEXT,
    created_at   INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    tool_name   TEXT,
    payload     TEXT,
    created_at  INTEGER NOT NULL
);
"""


class AgentDB:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or _DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def create_tables(self):
        with self._conn() as conn:
            conn.executescript(DDL)

    # ── 会话 CRUD ────────────────────────────────────────────────────────────

    def create_session(self, provider: str = '', model: str = '') -> str:
        session_id = uuid.uuid4().hex
        now = int(time.time())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions(session_id,provider,model,created_at,updated_at) VALUES(?,?,?,?,?)",
                (session_id, provider, model, now, now),
            )
        return session_id

    def get_session(self, session_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id=?", (session_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_sessions(self, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE is_archived=0 ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_session(self, session_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))

    def update_session_title(self, session_id: str, title: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET title=?,updated_at=? WHERE session_id=?",
                (title, int(time.time()), session_id),
            )

    def _touch_session(self, conn: sqlite3.Connection, session_id: str):
        conn.execute(
            "UPDATE sessions SET updated_at=?,message_count=message_count+1 WHERE session_id=?",
            (int(time.time()), session_id),
        )

    # ── 消息 CRUD ────────────────────────────────────────────────────────────

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str = None,
        tool_calls: list = None,
        tool_call_id: str = None,
    ) -> int:
        tool_calls_json = json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None
        now = int(time.time())
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO messages(session_id,role,content,tool_calls,tool_call_id,created_at) VALUES(?,?,?,?,?,?)",
                (session_id, role, content, tool_calls_json, tool_call_id, now),
            )
            self._touch_session(conn, session_id)
        return cur.lastrowid

    def get_messages(self, session_id: str, limit: int = 60) -> list[dict]:
        """返回最近 limit 条消息（按时间顺序）"""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM (
                    SELECT * FROM messages WHERE session_id=? ORDER BY created_at DESC LIMIT ?
                ) ORDER BY created_at ASC
                """,
                (session_id, limit),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d['tool_calls']:
                d['tool_calls'] = json.loads(d['tool_calls'])
            result.append(d)
        return result

    # ── 审计日志 ─────────────────────────────────────────────────────────────

    def append_audit(
        self,
        session_id: str,
        event_type: str,
        tool_name: str = None,
        payload: dict = None,
    ):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO audit_log(session_id,event_type,tool_name,payload,created_at) VALUES(?,?,?,?,?)",
                (
                    session_id,
                    event_type,
                    tool_name,
                    json.dumps(payload, ensure_ascii=False) if payload else None,
                    int(time.time()),
                ),
            )
