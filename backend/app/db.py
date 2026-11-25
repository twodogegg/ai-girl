"""SQLite 持久化：用户、人设、会话、消息、记忆、文件。

单文件 SQLite + WAL，适合单机起步；所有查询都走参数绑定。业务上不需要外键级联，
但保留外键约束，删用户时手动清理关联数据。
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    disabled INTEGER NOT NULL DEFAULT 0,
    adult_confirmed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS personas (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    published INTEGER NOT NULL DEFAULT 1,
    sort INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    persona_id TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_message_at TEXT NOT NULL,
    UNIQUE(user_id, persona_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    parts TEXT NOT NULL DEFAULT '[]',
    meta TEXT NOT NULL DEFAULT '{}',
    seq INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS messages_conversation_seq ON messages(conversation_id, seq);
CREATE INDEX IF NOT EXISTS conversations_user_last ON conversations(user_id, last_message_at DESC);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    content TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'fact',
    importance INTEGER NOT NULL DEFAULT 2,
    created_at TEXT NOT NULL,
    last_used_at TEXT
);

CREATE INDEX IF NOT EXISTS memories_pair ON memories(user_id, persona_id, importance DESC, created_at DESC);

CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    owner_user_id TEXT,
    kind TEXT NOT NULL,
    mime TEXT NOT NULL,
    size INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    path TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS files_owner ON files(owner_user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS admin_audit (
    id TEXT PRIMARY KEY,
    actor_id TEXT,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.conn: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()

    async def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn is not None:
            await self.conn.close()
            self.conn = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self.conn is None:
            raise RuntimeError("database is not open")
        return self.conn

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> aiosqlite.Cursor:
        async with self._write_lock:
            cursor = await self.db.execute(sql, params)
            await self.db.commit()
            return cursor

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        cursor = await self.db.execute(sql, params)
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        cursor = await self.db.execute(sql, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]

    @asynccontextmanager
    async def transaction(self):
        async with self._write_lock:
            await self.db.execute("BEGIN IMMEDIATE")
            try:
                yield self.db
            except Exception:
                await self.db.rollback()
                raise
            else:
                await self.db.commit()
