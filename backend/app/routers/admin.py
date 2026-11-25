"""后台：人设、Skills、工具目录与用户概览。只有 admin 可访问。"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Request

from ..db import Database, now
from ..errors import AppError
from ..security import admin_user
from ..services import personas as persona_service
from ..services.tools import TOOLS

router = APIRouter(prefix="/api/admin", tags=["后台"])


def _db(request: Request) -> Database:
    return request.app.state.db


def _normalize_persona(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    base = {**(existing or {}), **(payload or {})}
    persona_id = str(payload.get("id") or base.get("id") or "").strip()
    if not persona_id:
        raise AppError("人设 id 不能为空。", 400)
    if not all(char.isalnum() or char in "-_" for char in persona_id):
        raise AppError("人设 id 只能包含字母、数字、下划线和短横线。", 400)
    if not str(base.get("name") or "").strip():
        raise AppError("人设名称不能为空。", 400)
    try:
        age = int(base.get("age") or 0)
    except (TypeError, ValueError):
        age = 0
    if age < 18:
        raise AppError("所有人设必须是 18 岁以上的成年人。", 400)
    base["age"] = age
    tool_ids = [tool_id for tool_id in (base.get("toolIds") or []) if tool_id in TOOLS]
    base["toolIds"] = tool_ids
    base["skillIds"] = [str(item) for item in (base.get("skillIds") or []) if str(item).strip()]
    base["tags"] = [str(item) for item in (base.get("tags") or []) if str(item).strip()][:8]
    base["starters"] = [str(item) for item in (base.get("starters") or []) if str(item).strip()][:4]
    base["languages"] = [str(item) for item in (base.get("languages") or []) if str(item).strip()][:4]
    base["palette"] = [str(item) for item in (base.get("palette") or ["#3a2a1e", "#c9974c"])][:2]
    base["id"] = persona_id
    return base


@router.get("/overview")
async def overview(request: Request, _: dict = Depends(admin_user)):
    db = _db(request)
    counts = {}
    for name, sql in (
        ("users", "SELECT COUNT(*) AS n FROM users WHERE role = 'user'"),
        ("conversations", "SELECT COUNT(*) AS n FROM conversations"),
        ("messages", "SELECT COUNT(*) AS n FROM messages"),
        ("personas", "SELECT COUNT(*) AS n FROM personas"),
        ("skills", "SELECT COUNT(*) AS n FROM skills"),
        ("memories", "SELECT COUNT(*) AS n FROM memories"),
    ):
        row = await db.fetchone(sql)
        counts[name] = row["n"] if row else 0
    recent = await db.fetchall(
        """SELECT c.id, c.created_at, c.last_message_at, p.data AS persona, u.display_name
           FROM conversations c
           JOIN users u ON u.id = c.user_id
           LEFT JOIN personas p ON p.id = c.persona_id
           ORDER BY c.last_message_at DESC LIMIT 8"""
    )
    recent_out = []
    for row in recent:
        persona = json.loads(row["persona"]) if row.get("persona") else {}
        recent_out.append({
            "id": row["id"], "displayName": row["display_name"],
            "personaName": persona.get("nameZh") or persona.get("name") or row["id"],
            "lastMessageAt": row["last_message_at"],
        })
    return {"counts": counts, "recent": recent_out}


@router.get("/personas")
async def admin_personas(request: Request, _: dict = Depends(admin_user)):
    return {"personas": await persona_service.list_personas(_db(request), include_drafts=True)}


@router.post("/personas")
async def create_persona(request: Request, _: dict = Depends(admin_user)):
    body = await request.json()
    persona = _normalize_persona(body)
    if await _db(request).fetchone("SELECT id FROM personas WHERE id = ?", (persona["id"],)):
        raise AppError("这个人设 id 已经存在。", 409)
    await persona_service.save_persona(_db(request), persona)
    return {"persona": persona}


@router.put("/personas/{persona_id}")
async def update_persona(persona_id: str, request: Request, _: dict = Depends(admin_user)):
    db = _db(request)
    existing = await persona_service.load_persona(db, persona_id, include_drafts=True)
    body = await request.json()
    body["id"] = persona_id
    persona = _normalize_persona(body, existing)
    await persona_service.save_persona(db, persona)
    return {"persona": persona}


@router.delete("/personas/{persona_id}")
async def delete_persona(persona_id: str, request: Request, _: dict = Depends(admin_user)):
    await persona_service.delete_persona(_db(request), persona_id)
    return {"ok": True}


@router.get("/skills")
async def admin_skills(request: Request, _: dict = Depends(admin_user)):
    return {"skills": await persona_service.list_skills(_db(request))}


@router.post("/skills")
async def create_skill(request: Request, _: dict = Depends(admin_user)):
    body = await request.json()
    skill = await persona_service.save_skill(_db(request), body)
    return {"skill": skill}


@router.put("/skills/{skill_id}")
async def update_skill(skill_id: str, request: Request, _: dict = Depends(admin_user)):
    body = await request.json()
    body["id"] = skill_id
    skill = await persona_service.save_skill(_db(request), body)
    return {"skill": skill}


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str, request: Request, _: dict = Depends(admin_user)):
    await persona_service.delete_skill(_db(request), skill_id)
    return {"ok": True}


@router.get("/tools")
async def admin_tools(request: Request, _: dict = Depends(admin_user)):
    settings = request.app.state.settings
    availability = {
        "send_photo": settings.images_enabled,
        "send_voice": settings.tts_enabled,
    }
    return {"tools": [
        {"id": spec.id, "title": spec.title, "description": spec.description, "risk": spec.risk,
         "available": availability.get(spec.id, True)}
        for spec in TOOLS.values()
    ]}


@router.get("/users")
async def admin_users(request: Request, _: dict = Depends(admin_user)):
    rows = await _db(request).fetchall(
        """SELECT id, username, display_name, role, disabled, adult_confirmed_at, created_at
           FROM users ORDER BY created_at DESC LIMIT 200"""
    )
    return {"users": [
        {"id": row["id"], "username": row["username"], "displayName": row["display_name"],
         "role": row["role"], "disabled": bool(row["disabled"]),
         "adultConfirmed": bool(row["adult_confirmed_at"]), "createdAt": row["created_at"]}
        for row in rows
    ]}


@router.post("/users/{user_id}/disable")
async def disable_user(user_id: str, request: Request, _: dict = Depends(admin_user)):
    body = await request.json()
    disabled = 1 if body.get("disabled") else 0
    await _db(request).execute("UPDATE users SET disabled = ? WHERE id = ? AND role != 'admin'", (disabled, user_id))
    await _db(request).execute(
        "INSERT INTO admin_audit (id, actor_id, action, target, detail, created_at) VALUES (lower(hex(randomblob(12))), ?, ?, ?, ?, ?)",
        (_["id"], "user.disable" if disabled else "user.enable", user_id, "", now()),
    )
    return {"ok": True}
