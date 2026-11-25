"""公开人设、会话读取。人设的提示词 / 工具 / Skills 只在后台接口返回。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from ..db import Database
from ..errors import AppError
from ..security import adult_user, user_from_request
from ..services import conversations
from ..services import memory as memory_service
from ..services.personas import list_personas, load_persona, public_persona

router = APIRouter(prefix="/api", tags=["人设与会话"])


def _db(request: Request) -> Database:
    return request.app.state.db


@router.get("/personas")
async def personas(request: Request, q: str = "", tag: str = ""):
    db = _db(request)
    items = await list_personas(db)
    query = q.strip().lower()
    if query:
        items = [item for item in items if query in " ".join(
            str(item.get(key) or "") for key in ("name", "nameZh", "occupation", "tagline", "bio", "city")
        ).lower()]
    if tag:
        items = [item for item in items if tag in (item.get("tags") or [])]
    user = await user_from_request(request)
    existing: dict[str, dict] = {}
    if user:
        rows = await db.fetchall("SELECT * FROM conversations WHERE user_id = ?", (user["id"],))
        existing = {row["persona_id"]: row for row in rows}
    return {"personas": [public_persona(item, conversation=existing.get(item["id"])) for item in items]}


@router.get("/personas/{persona_id}")
async def persona_detail(persona_id: str, request: Request):
    db = _db(request)
    persona = await load_persona(db, persona_id)
    user = await user_from_request(request)
    conversation = await conversations.get_by_persona(db, user["id"], persona_id) if user else None
    return {"persona": public_persona(persona, conversation=conversation)}


@router.post("/personas/{persona_id}/open")
async def open_persona(persona_id: str, request: Request, user: dict = Depends(adult_user)):
    db = _db(request)
    persona = await load_persona(db, persona_id)
    conversation, _ = await conversations.ensure_conversation(db, user["id"], persona)
    rows = await conversations.list_messages(db, conversation["id"], limit=100)
    return {
        "conversation": conversations.conversation_public(conversation, persona),
        "persona": public_persona(persona, conversation=conversation),
        "messages": [conversations.message_public(row, request.app.state.media) for row in rows],
    }


@router.get("/conversations")
async def conversations_list(request: Request, user: dict = Depends(adult_user)):
    return {"conversations": await conversations.list_conversations(_db(request), user["id"])}


@router.get("/conversations/{conversation_id}")
async def conversation_detail(conversation_id: str, request: Request, user: dict = Depends(adult_user)):
    db = _db(request)
    row = await conversations.get_conversation(db, user["id"], conversation_id)
    if row is None:
        raise AppError("这段对话还不存在。", 404)
    persona = await load_persona(db, row["persona_id"])
    rows = await conversations.list_messages(db, conversation_id, limit=100)
    return {
        "conversation": conversations.conversation_public(row, persona),
        "persona": public_persona(persona, conversation=row),
        "messages": [conversations.message_public(message, request.app.state.media) for message in rows],
    }


@router.get("/conversations/{conversation_id}/messages")
async def conversation_messages(conversation_id: str, request: Request,
                                before: int | None = Query(default=None),
                                limit: int = Query(default=40, ge=1, le=100),
                                user: dict = Depends(adult_user)):
    db = _db(request)
    row = await conversations.get_conversation(db, user["id"], conversation_id)
    if row is None:
        raise AppError("这段对话还不存在。", 404)
    rows = await conversations.list_messages(db, conversation_id, limit=limit + 1, before_seq=before)
    has_more = len(rows) > limit
    rows = rows[-limit:] if has_more else rows
    return {
        "messages": [conversations.message_public(message, request.app.state.media) for message in rows],
        "hasMore": has_more,
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, request: Request, user: dict = Depends(adult_user)):
    await conversations.delete_conversation(_db(request), user["id"], conversation_id)
    return {"ok": True}


@router.get("/conversations/{conversation_id}/memories")
async def conversation_memories(conversation_id: str, request: Request, user: dict = Depends(adult_user)):
    db = _db(request)
    row = await conversations.get_conversation(db, user["id"], conversation_id)
    if row is None:
        raise AppError("这段对话还不存在。", 404)
    return {"memories": await memory_service.list_memories(db, user["id"], row["persona_id"])}


@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, request: Request, user: dict = Depends(adult_user)):
    await memory_service.delete_memory(_db(request), user["id"], memory_id)
    return {"ok": True}
