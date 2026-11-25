"""会话与消息。"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from ..db import Database, now
from .personas import default_state, normalize_state

MESSAGE_ROLES = {"user", "assistant", "system"}


def _json(value: str | None, fallback):
    try:
        return json.loads(value) if value else fallback
    except (TypeError, ValueError):
        return fallback


def _days_known(created_at: str) -> int:
    try:
        start = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return 1
    return max(1, (datetime.now(UTC) - start).days + 1)


def conversation_public(row: dict[str, Any], persona: dict[str, Any] | None = None,
                        preview: str | None = None) -> dict[str, Any]:
    state = normalize_state(_json(row.get("state"), {}))
    state["daysKnown"] = _days_known(row["created_at"])
    result = {
        "id": row["id"],
        "personaId": row["persona_id"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "lastMessageAt": row["last_message_at"],
        "state": state,
    }
    if persona:
        result["persona"] = {
            "id": persona.get("id"), "name": persona.get("name"), "nameZh": persona.get("nameZh"),
            "age": persona.get("age"), "occupation": persona.get("occupation"), "tagline": persona.get("tagline"),
            "palette": persona.get("palette"), "tags": persona.get("tags"),
        }
    if preview is not None:
        result["preview"] = preview
    return result


async def get_conversation(db: Database, user_id: str, conversation_id: str) -> dict[str, Any] | None:
    return await db.fetchone("SELECT * FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id))


async def get_by_persona(db: Database, user_id: str, persona_id: str) -> dict[str, Any] | None:
    return await db.fetchone("SELECT * FROM conversations WHERE user_id = ? AND persona_id = ?", (user_id, persona_id))


async def ensure_conversation(db: Database, user_id: str, persona: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    existing = await get_by_persona(db, user_id, persona["id"])
    if existing:
        return existing, False
    stamp = now()
    conversation_id = uuid.uuid4().hex
    state = default_state()
    cursor = await db.execute(
        """INSERT OR IGNORE INTO conversations (id, user_id, persona_id, state, created_at, updated_at, last_message_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (conversation_id, user_id, persona["id"], json.dumps(state, ensure_ascii=False), stamp, stamp, stamp),
    )
    created = bool(cursor.rowcount)
    if created:
        greeting = str(persona.get("greeting") or "").strip()
        if greeting:
            await add_message(db, conversation_id, "assistant", greeting, meta={"kind": "greeting"})
    row = await get_conversation(db, user_id, conversation_id) or await get_by_persona(db, user_id, persona["id"])
    assert row is not None
    return row, created


async def list_conversations(db: Database, user_id: str) -> list[dict[str, Any]]:
    rows = await db.fetchall(
        "SELECT * FROM conversations WHERE user_id = ? ORDER BY last_message_at DESC", (user_id,)
    )
    personas = {
        row["id"]: _json(row["data"], {})
        for row in await db.fetchall("SELECT id, data FROM personas")
    }
    result = []
    for row in rows:
        last = await db.fetchone(
            "SELECT content FROM messages WHERE conversation_id = ? ORDER BY seq DESC LIMIT 1", (row["id"],)
        )
        preview = (last or {}).get("content", "")
        result.append(conversation_public(row, personas.get(row["persona_id"]), preview[:90]))
    return result


async def touch_conversation(db: Database, conversation_id: str) -> None:
    stamp = now()
    await db.execute("UPDATE conversations SET updated_at = ?, last_message_at = ? WHERE id = ?", (stamp, stamp, conversation_id))


async def update_state(db: Database, conversation_id: str, state: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_state(state)
    await db.execute(
        "UPDATE conversations SET state = ?, updated_at = ? WHERE id = ?",
        (json.dumps(normalized, ensure_ascii=False), now(), conversation_id),
    )
    return normalized


async def add_message(db: Database, conversation_id: str, role: str, content: str,
                      parts: list[dict[str, Any]] | None = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    if role not in MESSAGE_ROLES:
        raise ValueError(f"invalid role: {role}")
    message_id = uuid.uuid4().hex
    stamp = now()
    async with db.transaction() as conn:
        cursor = await conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 AS next FROM messages WHERE conversation_id = ?",
                                    (conversation_id,))
        row = await cursor.fetchone()
        seq = int(row["next"])
        await conn.execute(
            """INSERT INTO messages (id, conversation_id, role, content, parts, meta, seq, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (message_id, conversation_id, role, content, json.dumps(parts or [], ensure_ascii=False),
             json.dumps(meta or {}, ensure_ascii=False), seq, stamp),
        )
        await conn.execute("UPDATE conversations SET updated_at = ?, last_message_at = ? WHERE id = ?",
                           (stamp, stamp, conversation_id))
    record = await db.fetchone("SELECT * FROM messages WHERE id = ?", (message_id,))
    assert record is not None
    return record


async def update_message(db: Database, message_id: str, *, content: str | None = None,
                         parts: list[dict[str, Any]] | None = None,
                         meta: dict[str, Any] | None = None) -> None:
    fields, values = [], []
    if content is not None:
        fields.append("content = ?")
        values.append(content)
    if parts is not None:
        fields.append("parts = ?")
        values.append(json.dumps(parts, ensure_ascii=False))
    if meta is not None:
        fields.append("meta = ?")
        values.append(json.dumps(meta, ensure_ascii=False))
    if not fields:
        return
    values.append(message_id)
    await db.execute(f"UPDATE messages SET {', '.join(fields)} WHERE id = ?", tuple(values))


async def list_messages(db: Database, conversation_id: str, *, limit: int = 60,
                        before_seq: int | None = None) -> list[dict[str, Any]]:
    if before_seq:
        rows = await db.fetchall(
            """SELECT * FROM messages WHERE conversation_id = ? AND seq < ?
               ORDER BY seq DESC LIMIT ?""",
            (conversation_id, before_seq, limit),
        )
    else:
        rows = await db.fetchall(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY seq DESC LIMIT ?",
            (conversation_id, limit),
        )
    return list(reversed(rows))


async def context_messages(db: Database, conversation_id: str, limit: int) -> list[dict[str, Any]]:
    return await list_messages(db, conversation_id, limit=limit)


async def delete_conversation(db: Database, user_id: str, conversation_id: str) -> None:
    row = await get_conversation(db, user_id, conversation_id)
    if row is None:
        return
    await db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    await db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


def message_public(row: dict[str, Any], media=None) -> dict[str, Any]:
    parts = _json(row.get("parts"), [])
    if media is not None:
        for part in parts:
            if isinstance(part, dict) and part.get("type") in {"image", "voice"} and part.get("fileId") and not part.get("url"):
                part["url"] = f"/api/files/{part['fileId']}"
    return {
        "id": row["id"],
        "role": row["role"],
        "content": row["content"],
        "parts": parts,
        "meta": _json(row.get("meta"), {}),
        "seq": row["seq"],
        "createdAt": row["created_at"],
    }
