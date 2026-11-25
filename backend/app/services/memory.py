"""长期记忆：模型通过工具写入，每轮把最重要的若干条注入系统提示。"""

from __future__ import annotations

import uuid
from typing import Any

from ..db import Database, now


async def add_memory(db: Database, user_id: str, persona_id: str, content: str,
                     *, kind: str = "fact", importance: int = 2) -> dict[str, Any]:
    text = " ".join(str(content or "").split()).strip()
    if not text:
        raise ValueError("记忆内容不能为空")
    text = text[:600]
    existing = await db.fetchone(
        "SELECT * FROM memories WHERE user_id = ? AND persona_id = ? AND content = ?",
        (user_id, persona_id, text),
    )
    if existing:
        await db.execute("UPDATE memories SET importance = MAX(importance, ?), last_used_at = ? WHERE id = ?",
                         (importance, now(), existing["id"]))
        existing["importance"] = max(int(existing["importance"]), importance)
        return existing
    memory_id = uuid.uuid4().hex
    stamp = now()
    await db.execute(
        """INSERT INTO memories (id, user_id, persona_id, content, kind, importance, created_at, last_used_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (memory_id, user_id, persona_id, text, kind[:32], max(1, min(5, int(importance))), stamp, stamp),
    )
    record = await db.fetchone("SELECT * FROM memories WHERE id = ?", (memory_id,))
    assert record is not None
    return record


async def top_memories(db: Database, user_id: str, persona_id: str, limit: int = 14) -> list[dict[str, Any]]:
    return await db.fetchall(
        """SELECT * FROM memories WHERE user_id = ? AND persona_id = ?
           ORDER BY importance DESC, created_at DESC LIMIT ?""",
        (user_id, persona_id, limit),
    )


async def search_memories(db: Database, user_id: str, persona_id: str, query: str,
                          limit: int = 8) -> list[dict[str, Any]]:
    text = str(query or "").strip()
    if not text:
        return await top_memories(db, user_id, persona_id, limit)
    rows = await db.fetchall(
        """SELECT * FROM memories WHERE user_id = ? AND persona_id = ? AND content LIKE ?
           ORDER BY importance DESC, created_at DESC LIMIT ?""",
        (user_id, persona_id, f"%{text[:40]}%", limit),
    )
    if not rows:
        rows = await top_memories(db, user_id, persona_id, limit)
    if rows:
        ids = [row["id"] for row in rows]
        placeholders = ",".join("?" for _ in ids)
        await db.execute(f"UPDATE memories SET last_used_at = ? WHERE id IN ({placeholders})", (now(), *ids))
    return rows


async def list_memories(db: Database, user_id: str, persona_id: str, limit: int = 100) -> list[dict[str, Any]]:
    return await db.fetchall(
        "SELECT * FROM memories WHERE user_id = ? AND persona_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, persona_id, limit),
    )


async def delete_memory(db: Database, user_id: str, memory_id: str) -> None:
    await db.execute("DELETE FROM memories WHERE id = ? AND user_id = ?", (memory_id, user_id))
