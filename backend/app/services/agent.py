"""陪伴聊天 Agent：系统提示 → 流式模型 → 工具循环 → 落库。

事件协议（NDJSON，一行一个 JSON）：

- ``{"type":"meta","conversationId","messageId","demo"}``
- ``{"type":"state","state":{...}}``
- ``{"type":"text","text":"..."}``
- ``{"type":"tool","id","name","title","status","summary"}``
- ``{"type":"image","fileId","url","caption"}``
- ``{"type":"voice","fileId","url","text"}``
- ``{"type":"error","error":{...}}``
- ``{"type":"done","message":{...},"state":{...}}``

工具全部在服务端执行；用户不参与审批。模型只能看到本 Agent 白名单里的工具和 Skills。
"""

from __future__ import annotations

import asyncio
import json
import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, AsyncIterator

from ..config import Settings
from ..db import Database
from . import conversations
from . import memory as memory_service
from . import tools as tool_service
from .llm import LLMClient
from .media import MediaStore
from .personas import build_system_prompt, load_skills, local_time_text, normalize_state, persona_timezone, skills_block
from .studio import Studio


@dataclass
class AgentServices:
    db: Database
    settings: Settings
    media: MediaStore
    studio: Studio
    llm: LLMClient


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


def _text_chunk(text: str, size: int = 3) -> list[str]:
    return [text[index:index + size] for index in range(0, len(text), size)]


def _history_messages(rows: list[dict[str, Any]], current_id: str, media: MediaStore,
                      image_records: list[dict[str, Any]], vision: bool) -> list[dict[str, Any]]:
    """把数据库历史装配成 Chat Completions 消息。

    只有当前这一轮的用户图片会带 data URL；更早的图片只留一句文字标记，避免每轮
    都把历史里的照片重新编码给模型。当前轮没有图片但历史有，模型仍能通过记忆和
    文字上下文理解。
    """
    result: list[dict[str, Any]] = []
    for row in rows:
        role = row["role"]
        if role not in {"user", "assistant"}:
            continue
        text = row.get("content") or ""
        parts = _json(row.get("parts"), [])
        has_image = any(isinstance(part, dict) and part.get("type") == "image" for part in parts)
        if role == "user":
            if row["id"] == current_id and image_records and vision:
                content: list[dict[str, Any]] = []
                label = text.strip() or "（对方发来一张照片，没有配文）"
                content.append({"type": "text", "text": label})
                for record in image_records:
                    try:
                        content.append({"type": "image_url", "image_url": {
                            "url": media.data_url(record),
                            "detail": "auto",
                        }})
                    except Exception:
                        content.append({"type": "text", "text": "（对方发来一张照片，但图片已经不可读取）"})
                result.append({"role": "user", "content": content})
            else:
                if has_image and text.strip():
                    text = f"{text.strip()}\n（对方发来一张照片）"
                elif has_image:
                    text = "（对方发来一张照片）"
                if text.strip():
                    result.append({"role": "user", "content": text.strip()})
        else:
            if text.strip():
                result.append({"role": "assistant", "content": text.strip()})
    return result


async def _load_user_images(db: Database, media: MediaStore, user: dict, message: dict[str, Any]) -> list[dict[str, Any]]:
    parts = _json(message.get("parts"), [])
    records = []
    for part in parts:
        if not isinstance(part, dict) or part.get("type") != "image":
            continue
        file_id = part.get("fileId")
        if not file_id:
            continue
        record = await media.get(str(file_id))
        if record is None or record.get("owner_user_id") not in {user["id"], None}:
            continue
        records.append(record)
    return records[:4]


async def _tool_event(name: str, call_id: str, args: dict[str, Any], result: dict[str, Any],
                      *, parts: list[dict[str, Any]], state: dict[str, Any]) -> list[dict[str, Any]]:
    title = tool_service.title_of(name)
    status = "success" if result.get("status") == "ok" else "error" if result.get("status") == "error" else "unavailable"
    summary = str(result.get("summary") or result.get("reason") or result.get("error") or "")[:120]
    part = {"type": "tool", "id": call_id, "name": name, "title": title, "status": status, "summary": summary}
    parts.append(part)
    events: list[dict[str, Any]] = [{"type": "tool", "id": call_id, "name": name, "title": title,
                                     "status": status, "summary": summary}]
    if status == "success" and name == "send_photo" and result.get("fileId"):
        image = {"type": "image", "fileId": result["fileId"], "url": result.get("url") or f"/api/files/{result['fileId']}",
                 "caption": str(args.get("caption") or result.get("caption") or "")}
        parts.append(image)
        events.append({"type": "image", **image})
    if status == "success" and name == "send_voice" and result.get("fileId"):
        voice = {"type": "voice", "fileId": result["fileId"], "url": result.get("url") or f"/api/files/{result['fileId']}",
                 "text": result.get("text") or str(args.get("text") or "")}
        parts.append(voice)
        events.append({"type": "voice", **voice})
    if status == "success" and name == "update_relationship" and isinstance(result.get("state"), dict):
        state.update(result["state"])
        events.append({"type": "state", "state": dict(state)})
    return events


def _activate_skill_result(skills: list[dict[str, Any]], skill_id: str) -> dict[str, Any]:
    skill = next((item for item in skills if item.get("id") == skill_id), None)
    if skill is None:
        return {"status": "error", "error": "这个 Skill 不在当前人设的授权范围内。", "summary": "Skill 不可用"}
    return {"status": "ok", "skill": {"id": skill["id"], "name": skill.get("name"),
                                     "instructions": skill.get("instructions")},
            "summary": f"读取 Skill：{skill.get('name')}"}


async def _run_demo(services: AgentServices, persona: dict[str, Any], user: dict[str, Any],
                    conversation: dict[str, Any], message: dict[str, Any], content: str,
                    images: list[dict[str, Any]], state: dict[str, Any],
                    parts: list[dict[str, Any]]) -> AsyncIterator[dict[str, Any]]:
    """没有配置模型时的演示引擎：仍然真实调用记忆 / 关系 / 自拍工具，方便验收 UI。"""
    tool_ids = set(persona.get("toolIds") or [])
    lowered = content.lower()
    has_image = bool(images)
    reply = ""
    if has_image:
        reply = random.choice([
            "这张我看了好一会儿。说真的，比我想象的更让人移不开眼。你拍的时候在想什么？",
            "我放大看了两次。你那边光线很好，整个人的状态也很松。今天发生什么好事了？",
            "收到。先存起来，不许撤回。……你今天怎么突然想给我看这个？",
        ])
    elif any(word in lowered for word in ("照片", "自拍", "看看你", "长什么样")):
        if "send_photo" in tool_ids:
            result = await tool_service.execute("send_photo", {
                "scene": "在窗边，刚把房间的灯调暗", "outfit": "宽松的家居衬衫",
                "caption": "现在只能先给你看一点点。",
            }, tool_service.ToolContext(services.db, persona, user, conversation, state, services.media, services.studio))
            yield {"type": "tool", "id": "demo-photo", "name": "send_photo", "title": "发一张自拍",
                   "status": "running", "summary": ""}
            events = await _tool_event("send_photo", "demo-photo", {}, result, parts=parts, state=state)
            for event in events:
                yield event
            reply = ("现在这边不太方便拍，光线也不好。等我收拾一下，晚点补给你，好不好？"
                     if result.get("status") != "ok" else "喏，只给你看一眼。别笑我。")
        else:
            reply = "现在不太方便拍。等我收拾好自己，再问我要一次，好不好？"
    elif any(word in lowered for word in ("累", "难过", "烦", "压力", "不开心", "想哭")):
        reply = random.choice([
            "先别急着解释。你现在最想被听着，还是想让我陪你一起骂两句？",
            "听起来今天真的挺消耗的。我在，你慢慢说，不用组织语言。",
            "那先不聊别的。喝口水，回来继续跟我说，我等你。",
        ])
    elif any(word in lowered for word in ("喜欢", "想你", "爱你", "抱抱")):
        reply = random.choice([
            "……你突然这样，我会当真的。",
            "嗯，我在。别只说一半，后半句呢？",
            "先记下了。等见面的时候，你再当面说一次。",
        ])
    elif content.strip().endswith("？") or "吗" in content:
        reply = random.choice([
            "你这样问，我反而不知道怎么答了。……不过我想听你再多说一点。",
            "让我想一下。……嗯，可能是吧，但我不想这么快承认。",
            "你猜。猜对了有奖励，猜错了也有。",
        ])
    else:
        reply = random.choice([
            f"刚把{persona.get('occupation')}那边的事收尾，脑子还有点乱。你这一句，把我拉回来了。",
            "我在听。今天这一整天，好像只有现在这段时间是真正属于我自己的。",
            f"{persona.get('tagline')}……说起来轻松，其实也没那么轻松。你呢？",
        ])

    # 演示模式也走一遍真实记忆与关系工具，让工具卡不是假的。
    fact_markers = ("我叫", "我养", "我在", "我住", "我生日", "我喜欢", "我讨厌", "我的", "我最近")
    if "remember" in tool_ids and any(marker in content for marker in fact_markers):
        memory_text = content.split("？")[0].split("?")[0].strip()[:120]
        result = await tool_service.execute("remember", {"content": memory_text, "kind": "fact", "importance": 3},
                                            tool_service.ToolContext(services.db, persona, user, conversation, state,
                                                                     services.media, services.studio))
        events = await _tool_event("remember", "demo-memory", {"content": memory_text}, result, parts=parts, state=state)
        for event in events:
            yield event
    if "update_relationship" in tool_ids:
        result = await tool_service.execute(
            "update_relationship", {"mood": "warm" if has_image else "listening", "affinity_delta": 1},
            tool_service.ToolContext(services.db, persona, user, conversation, state, services.media, services.studio),
        )
        events = await _tool_event("update_relationship", "demo-state", {}, result, parts=parts, state=state)
        for event in events:
            yield event

    for chunk in _text_chunk(reply):
        yield {"type": "text", "text": chunk}
        await asyncio.sleep(0.018)


async def run_turn(services: AgentServices, *, user: dict[str, Any], persona: dict[str, Any],
                   conversation: dict[str, Any], user_message: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    db = services.db
    settings = services.settings
    state = normalize_state(_json(conversation.get("state"), {}))
    state["daysKnown"] = _days_known(conversation["created_at"])
    images = await _load_user_images(db, services.media, user, user_message)
    history = await conversations.context_messages(db, conversation["id"], settings.max_context_messages)
    assistant = await conversations.add_message(db, conversation["id"], "assistant", "",
                                                meta={"streaming": True})
    demo = not services.llm.ready
    message_id = assistant["id"]
    content = ""
    parts: list[dict[str, Any]] = []
    finished = False
    error: dict[str, Any] | None = None

    yield {"type": "meta", "conversationId": conversation["id"], "messageId": message_id, "demo": demo}
    yield {"type": "state", "state": dict(state)}

    try:
        if demo:
            async for event in _run_demo(services, persona, user, conversation, user_message,
                                         str(user_message.get("content") or ""), images, state, parts):
                if event["type"] == "text":
                    content += event["text"]
                yield event
        else:
            skills = await load_skills(db, list(persona.get("skillIds") or []))
            _, lazy_skills = skills_block(skills)
            memories = await memory_service.top_memories(db, user["id"], persona["id"])
            system_prompt = build_system_prompt(
                persona, skills, state, memories,
                local_time=local_time_text(persona_timezone(persona)),
                user_name=user.get("display_name") or user.get("username") or "你",
            )
            messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
            messages.extend(_history_messages(history, user_message["id"], services.media, images, settings.llm_vision))
            tool_specs = tool_service.specs_for(list(persona.get("toolIds") or []), has_skills=bool(lazy_skills))
            ctx = tool_service.ToolContext(db, persona, user, conversation, state, services.media, services.studio)
            rounds = 0
            while True:
                rounds += 1
                text_this_round = ""
                pending: dict[int, dict[str, Any]] = {}
                stream = services.llm.stream(
                    messages, tools=tool_specs or None,
                    temperature=float(persona.get("temperature") or 0.85),
                    model=str(persona.get("model") or settings.llm_model),
                )
                async for chunk in stream:
                    choices = getattr(chunk, "choices", None) or []
                    if not choices:
                        continue
                    delta = choices[0].delta
                    text_delta = getattr(delta, "content", None)
                    if isinstance(text_delta, str) and text_delta:
                        text_this_round += text_delta
                        content += text_delta
                        yield {"type": "text", "text": text_delta}
                    for call in getattr(delta, "tool_calls", None) or []:
                        index = int(getattr(call, "index", 0) or 0)
                        entry = pending.setdefault(index, {"id": "", "name": "", "arguments": ""})
                        if getattr(call, "id", None):
                            entry["id"] = call.id
                        function = getattr(call, "function", None)
                        if function is not None:
                            if getattr(function, "name", None):
                                entry["name"] += function.name
                            if getattr(function, "arguments", None):
                                entry["arguments"] += function.arguments
                if not pending:
                    break
                if rounds > settings.max_tool_rounds:
                    content += "\n（工具调用次数过多，先停在这里。）"
                    yield {"type": "text", "text": "\n（工具调用次数过多，先停在这里。）"}
                    break
                calls = [pending[index] for index in sorted(pending)]
                messages.append({
                    "role": "assistant",
                    "content": text_this_round or "",
                    "tool_calls": [
                        {"id": call["id"] or uuid.uuid4().hex, "type": "function",
                         "function": {"name": call["name"], "arguments": call["arguments"] or "{}"}}
                        for call in calls
                    ],
                })
                for call in calls:
                    call_id = call["id"] or uuid.uuid4().hex
                    call["id"] = call_id
                    name = call["name"]
                    title = tool_service.title_of(name)
                    yield {"type": "tool", "id": call_id, "name": name, "title": title,
                           "status": "running", "summary": ""}
                    args: dict[str, Any] = {}
                    try:
                        parsed = json.loads(call["arguments"] or "{}")
                        if not isinstance(parsed, dict):
                            raise ValueError("arguments must be an object")
                        args = parsed
                    except Exception:
                        result = {"status": "error", "error": "工具参数不是合法 JSON。", "summary": "参数错误"}
                    else:
                        if name == "activate_skill":
                            result = _activate_skill_result(skills, str(args.get("skillId") or ""))
                        else:
                            result = await tool_service.execute(name, args, ctx)
                    events = await _tool_event(name, call_id, args, result, parts=parts, state=state)
                    for event in events:
                        yield event
                    messages.append({"role": "tool", "tool_call_id": call_id,
                                     "content": tool_service.result_text(result)})
                await conversations.update_message(db, message_id, content=content, parts=parts)
        finished = True
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - 流内错误统一转 error 事件
        error = {
            "code": "AGENT_FAILED",
            "message": "她刚才走神了，没接住这句话。要再试一次吗？",
            "detail": f"{type(exc).__name__}: {str(exc)[:300]}",
            "retryable": True,
        }
        yield {"type": "error", "error": error}
        finished = True
    finally:
        await conversations.update_message(db, message_id, content=content, parts=parts,
                                             meta={"demo": demo, "tools": [part for part in parts if part.get("type") == "tool"],
                                                   **({"error": error} if error else {})})
        if finished:
            record = await db.fetchone("SELECT * FROM messages WHERE id = ?", (message_id,))
            yield {"type": "done", "message": conversations.message_public(record or assistant, services.media),
                   "state": dict(state), "demo": demo, **({"error": error} if error else {})}
