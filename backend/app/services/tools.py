"""服务端工具注册表。

与 darl-tv 的「浏览器执行 / 审批」不同，陪伴聊天里的工具都是服务端能力：
记忆、关系状态、生图、语音、时间。前端只消费工具事件（running / success / error），
不参与执行，用户也不需要批准。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from ..db import Database
from ..services import memory as memory_service
from ..services.conversations import update_state
from ..services.media import MediaStore
from ..services.personas import local_time_text, normalize_state
from ..services.studio import Studio, ToolUnavailable


@dataclass
class ToolContext:
    db: Database
    persona: dict[str, Any]
    user: dict[str, Any]
    conversation: dict[str, Any]
    state: dict[str, Any]
    media: MediaStore
    studio: Studio


Handler = Callable[[ToolContext, dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolSpec:
    id: str
    title: str
    description: str
    parameters: dict[str, Any]
    handler: Handler
    risk: str = "read"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.id,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def _obj(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or [], "additionalProperties": False}


async def _remember(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    record = await memory_service.add_memory(
        ctx.db, ctx.user["id"], ctx.persona["id"], str(args.get("content") or ""),
        kind=str(args.get("kind") or "fact"), importance=int(args.get("importance") or 2),
    )
    return {"status": "ok", "memory": record["content"], "kind": record["kind"],
            "summary": f"记住了：{record['content'][:42]}"}


async def _recall(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    rows = await memory_service.search_memories(
        ctx.db, ctx.user["id"], ctx.persona["id"], str(args.get("query") or ""), limit=8,
    )
    return {"status": "ok", "memories": [row["content"] for row in rows],
            "summary": f"想起 {len(rows)} 件事" if rows else "没有找到相关记忆"}


async def _relationship(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    state = normalize_state(ctx.state)
    delta = int(args.get("affinity_delta") or 0)
    state["affinity"] = max(0, min(100, int(state.get("affinity", 8)) + max(-3, min(3, delta))))
    state["mood"] = str(args.get("mood") or state.get("mood") or "curious")[:24]
    note = str(args.get("note") or "").strip()
    if note:
        milestones = list(state.get("milestones") or [])[-19:]
        milestones.append({"at": local_time_text(), "note": note[:120]})
        state["milestones"] = milestones
    updated = await update_state(ctx.db, ctx.conversation["id"], state)
    ctx.state.update(updated)
    return {"status": "ok", "state": updated, "summary": f"关系更新：{updated['stage']} · {updated['mood']}"}


async def _send_photo(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    scene = str(args.get("scene") or "在自己熟悉的空间里，随手举起手机自拍").strip()
    outfit = str(args.get("outfit") or "").strip()
    caption = str(args.get("caption") or "").strip()
    try:
        result = await ctx.studio.selfie(ctx.persona, scene=scene, outfit=outfit, caption=caption, owner=ctx.user["id"])
    except ToolUnavailable as error:
        return {"status": "unavailable", "reason": str(error), "summary": f"自拍发送失败：{error}"}
    return {"status": "ok", **result, "summary": "发了一张自拍"}


async def _send_voice(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    text = str(args.get("text") or "").strip()
    try:
        result = await ctx.studio.voice(text, voice=str(ctx.persona.get("voice") or ""), owner=ctx.user["id"])
    except ToolUnavailable as error:
        return {"status": "unavailable", "reason": str(error), "summary": f"语音发送失败：{error}"}
    return {"status": "ok", **result, "summary": "发了一条语音"}


async def _get_time(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "time": local_time_text(), "summary": "看了一眼时间"}


TOOLS: dict[str, ToolSpec] = {
    "remember": ToolSpec(
        "remember", "记住这件事",
        "把对方告诉你、值得长期记住的事实 / 偏好 / 重要日子写入长期记忆。只在确实重要时调用，不要复述整段对话。",
        _obj({
            "content": {"type": "string", "description": "一句完整、可独立理解的记忆，如「他养了一只叫年糕的橘猫」"},
            "kind": {"type": "string", "enum": ["fact", "preference", "date", "emotion", "promise"], "description": "记忆类型"},
            "importance": {"type": "integer", "minimum": 1, "maximum": 5, "description": "重要程度，1–5"},
        }, ["content"]),
        _remember, "write",
    ),
    "recall": ToolSpec(
        "recall", "翻找回忆",
        "需要回忆以前聊过的事情时使用；返回与你查询最相关的长期记忆。",
        _obj({"query": {"type": "string", "description": "要回忆的关键词，如「猫」「生日」「上次说的工作」"}}, ["query"]),
        _recall,
    ),
    "update_relationship": ToolSpec(
        "update_relationship", "更新关系",
        "对话出现明显的关系变化或情绪变化时更新状态。affinity_delta 每次只能在 -3 到 +3 之间。",
        _obj({
            "mood": {"type": "string", "description": "你此刻的情绪，如 relaxed / shy / teasing / missing_him / hurt"},
            "affinity_delta": {"type": "integer", "minimum": -3, "maximum": 3, "description": "关系亲密度变化"},
            "note": {"type": "string", "description": "值得记住的关系里程碑，没有就留空"},
        }, ["mood"]),
        _relationship, "write",
    ),
    "send_photo": ToolSpec(
        "send_photo", "发一张自拍",
        "生成并发送一张符合人设的日常自拍。内容是生活化、克制、非露骨的；对方明确想看时再用。",
        _obj({
            "scene": {"type": "string", "description": "拍摄场景，如「刚洗完澡，浴室镜子前有水汽」"},
            "outfit": {"type": "string", "description": "穿着，如「宽大的白色衬衫」；没有就留空"},
            "caption": {"type": "string", "description": "配文，一句对方能接话的短句"},
        }, ["scene", "caption"]),
        _send_photo, "write",
    ),
    "send_voice": ToolSpec(
        "send_voice", "发一条语音",
        "把一句短话生成语音发给对方。适合情绪浓度高的时刻；发之前先确认对方方便听。",
        _obj({
            "text": {"type": "string", "description": "要说的内容，口语化，控制在 60 字以内"},
            "emotion": {"type": "string", "description": "语气，如 soft / sleepy / playful"},
        }, ["text"]),
        _send_voice, "write",
    ),
    "get_time": ToolSpec(
        "get_time", "看一眼时间",
        "读取当前本地时间。需要知道今天是几号、几点、什么节日时使用。",
        _obj({}),
        _get_time,
    ),
}


def specs_for(persona_tool_ids: list[str], *, has_skills: bool) -> list[dict[str, Any]]:
    specs = [TOOLS[tool_id].schema() for tool_id in persona_tool_ids if tool_id in TOOLS]
    if has_skills:
        specs.append({
            "type": "function",
            "function": {
                "name": "activate_skill",
                "description": "读取一个可用 Skill 的完整说明。需要按某个 Skill 的步骤回应时调用，一次只激活当前要用的那个。",
                "parameters": _obj({"skillId": {"type": "string", "description": "Skill 的 id"}}, ["skillId"]),
            },
        })
    return specs


async def execute(name: str, args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    spec = TOOLS.get(name)
    if spec is None:
        return {"status": "error", "error": f"没有这个工具：{name}"}
    try:
        return await spec.handler(ctx, args)
    except Exception as error:  # noqa: BLE001 - 工具失败必须变成模型可读的结果
        return {"status": "error", "error": f"{type(error).__name__}: {error}", "summary": "工具执行失败"}


def title_of(name: str) -> str:
    if name == "activate_skill":
        return "读取 Skill"
    return TOOLS[name].title if name in TOOLS else name


def result_text(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False)
