"""流式聊天：NDJSON + 心跳 + 运行互斥。

客户端发送一条消息后消费流；连接断开时浏览器取消 fetch，服务端关闭生成器，
Agent 的 finally 会把已生成的部分回复落库。同一用户对同一人设同时只允许一轮运行。
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..db import Database
from ..errors import AppError
from ..security import adult_user
from ..services import conversations
from ..services.agent import AgentServices, run_turn
from ..services.personas import load_persona

router = APIRouter(prefix="/api/chat", tags=["聊天"])

HEARTBEAT_SECONDS = 15


class ChatInput(BaseModel):
    personaId: str
    conversationId: str | None = None
    text: str = Field(default="", max_length=4000)
    imageIds: list[str] = Field(default_factory=list, max_length=4)
    regenerate: bool = False


class ActiveRuns:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.keys: set[tuple[str, str]] = set()

    async def acquire(self, key: tuple[str, str]) -> bool:
        async with self.lock:
            if key in self.keys:
                return False
            self.keys.add(key)
            return True

    async def release(self, key: tuple[str, str]) -> None:
        async with self.lock:
            self.keys.discard(key)


def _line(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False) + "\n"


async def _with_heartbeat(source):
    queue: asyncio.Queue = asyncio.Queue(maxsize=64)

    async def pump() -> None:
        try:
            async for event in source:
                await queue.put(event)
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001
            await queue.put({"type": "error", "error": {
                "code": "AGENT_STREAM_FAILED", "message": "连接中断了。", "retryable": True,
                "detail": f"{type(error).__name__}: {error}",
            }})
        finally:
            await queue.put(None)

    task = asyncio.create_task(pump())
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), HEARTBEAT_SECONDS)
            except TimeoutError:
                yield _line({"type": "ping"})
                continue
            if event is None:
                break
            yield _line(event)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await source.aclose()


def _db(request: Request) -> Database:
    return request.app.state.db


@router.post("")
async def chat(data: ChatInput, request: Request, user: dict = Depends(adult_user)):
    app = request.app
    db = _db(request)
    settings = app.state.settings
    if not data.regenerate and not data.text.strip() and not data.imageIds:
        raise AppError("想说点什么，或者发一张照片。", 400)
    if not app.state.rate_limiter.allow(user["id"]):
        raise AppError("说得有点太快了，先喝口水，过一会儿再聊。", 429)

    persona = await load_persona(db, data.personaId)
    if data.conversationId:
        conversation = await conversations.get_conversation(db, user["id"], data.conversationId)
        if conversation is None:
            raise AppError("这段对话还不存在。", 404)
        if conversation["persona_id"] != persona["id"]:
            raise AppError("这段对话不属于当前人设。", 404)
    else:
        conversation = await conversations.get_by_persona(db, user["id"], persona["id"])
        if conversation is None:
            conversation, _ = await conversations.ensure_conversation(db, user["id"], persona)

    # 先拿运行锁，再写用户消息：否则并发请求被 409 拒绝时，用户消息已经落库，
    # 前端重试会出现两条相同的话。
    key = (user["id"], persona["id"])
    if not await app.state.active_chat_runs.acquire(key):
        raise AppError("她还在回你上一条，等她说完了再发。", 409)
    try:
        if data.regenerate:
            last_user = await db.fetchone(
                "SELECT * FROM messages WHERE conversation_id = ? AND role = 'user' ORDER BY seq DESC LIMIT 1",
                (conversation["id"],),
            )
            if last_user is None:
                raise AppError("还没有可以重答的消息。", 400)
            await db.execute(
                "DELETE FROM messages WHERE conversation_id = ? AND seq > ?",
                (conversation["id"], last_user["seq"]),
            )
            user_message = last_user
        else:
            parts: list[dict] = []
            for file_id in data.imageIds[:4]:
                record = await app.state.media.get(file_id)
                if record is None or record.get("owner_user_id") != user["id"]:
                    raise AppError("图片已失效，请重新上传。", 404)
                parts.append({"type": "image", "fileId": file_id})
            user_message = await conversations.add_message(
                db, conversation["id"], "user", data.text.strip(), parts=parts,
                meta={"clientMessageId": None},
            )
    except BaseException:
        await app.state.active_chat_runs.release(key)
        raise

    services = AgentServices(db=db, settings=settings, media=app.state.media,
                             studio=app.state.studio, llm=app.state.llm)

    async def generate():
        try:
            source = run_turn(services, user=user, persona=persona, conversation=conversation,
                              user_message=user_message)
            async for line in _with_heartbeat(source):
                yield line
        finally:
            await app.state.active_chat_runs.release(key)

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-store, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/capabilities")
async def capabilities(request: Request):
    settings = request.app.state.settings
    return {
        "demo": not settings.llm_ready,
        "vision": settings.llm_vision,
        "images": settings.images_enabled,
        "voice": settings.tts_enabled,
        "model": settings.llm_model if settings.llm_ready else "demo",
    }
