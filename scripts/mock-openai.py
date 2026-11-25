"""本地联调用的 OpenAI 兼容假服务。

- POST /v1/chat/completions：流式返回；按最后一轮内容决定调用 remember / send_photo / send_voice
  或直接说话，用来验证服务端工具循环与前端 NDJSON/工具卡。
- POST /v1/images/generations：返回一张测试图（base64）。
- POST /v1/audio/speech：返回一小段提示音（PCM 包装成 mp3 后缀，仅用于联调播放链路）。

运行：
    uv run --project backend python scripts/mock-openai.py
    LLM_BASE_URL=http://127.0.0.1:5196/v1 LLM_API_KEY=mock LLM_MODEL=mock \
    IMAGE_BASE_URL=http://127.0.0.1:5196/v1 IMAGE_API_KEY=mock \
    TTS_BASE_URL=http://127.0.0.1:5196/v1 TTS_API_KEY=mock \
    uv run --project backend python -m app
"""

from __future__ import annotations

import base64
import io
import json
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from PIL import Image, ImageDraw

app = FastAPI()


def test_image_b64() -> str:
    image = Image.new("RGB", (768, 1024), (28, 22, 18))
    draw = ImageDraw.Draw(image)
    for y in range(1024):
        shade = int(30 + 120 * (y / 1024))
        draw.line([(0, y), (768, y)], fill=(shade, int(shade * 0.72), int(shade * 0.42)))
    draw.ellipse([220, 220, 548, 620], outline=(232, 165, 50), width=3)
    draw.ellipse([330, 360, 360, 390], fill=(243, 240, 232))
    draw.ellipse([410, 360, 440, 390], fill=(243, 240, 232))
    draw.arc([330, 430, 450, 520], 20, 160, fill=(243, 240, 232), width=3)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=88)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


IMAGE_B64 = test_image_b64()


def chunk(content: str | None = None, tool_call: dict | None = None, finish: str | None = None) -> dict:
    delta: dict = {"role": "assistant"}
    if content is not None:
        delta["content"] = content
    if tool_call is not None:
        delta["tool_calls"] = [tool_call]
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "mock",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }


def user_text(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(part.get("text", "") for part in content if isinstance(part, dict))
    return ""


def has_image(messages: list[dict]) -> bool:
    for message in messages:
        content = message.get("content")
        if isinstance(content, list) and any(
            isinstance(part, dict) and part.get("type") in {"image_url", "input_image"} for part in content
        ):
            return True
    return False


def tool_call(name: str, arguments: dict) -> dict:
    return {
        "index": 0,
        "id": f"call_{name}",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)},
    }


@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages") or []
    last = messages[-1] if messages else {}
    text = user_text(messages)
    image = has_image(messages)

    async def stream():
        if last.get("role") == "tool":
            tool_content = last.get("content") or ""
            if "fileId" in tool_content and "send_photo" in tool_content:
                reply = "喏，刚拍的。只给你看一眼，别笑我。"
            elif "fileId" in tool_content and "send_voice" in tool_content:
                reply = "听到了吗？今天想用声音跟你说晚安。"
            elif "memory" in tool_content:
                reply = "我记住了。下次你再说累，我会先问你今天发生了什么。"
            else:
                reply = "好了，弄完了。你继续说，我在听。"
            for piece in [reply[: max(1, len(reply) // 2)], reply[max(1, len(reply) // 2):]]:
                if piece:
                    yield f"data: {json.dumps(chunk(piece), ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps(chunk(finish='stop'), ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return

        if image:
            reply = "我看到这张照片了。光线很软，你站在那儿的样子让我想多看一会儿。你拍的时候在想什么？"
            for piece in [reply[:18], reply[18:]]:
                yield f"data: {json.dumps(chunk(piece), ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps(chunk(finish='stop'), ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return

        if any(word in text for word in ("照片", "自拍", "看看你", "长什么样")):
            call = tool_call("send_photo", {"scene": "在窗边，房间只开了一盏暖灯", "outfit": "宽松的白衬衫", "caption": "喏，刚拍的。"})
        elif "语音" in text:
            call = tool_call("send_voice", {"text": "今天辛苦了，早点睡。我在这儿。", "emotion": "soft"})
        else:
            call = tool_call("remember", {"content": "他今天有点累，喜欢海边", "kind": "fact", "importance": 4})
        yield f"data: {json.dumps(chunk(tool_call=call), ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps(chunk(finish='tool_calls'), ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/v1/images/generations")
async def images():
    return JSONResponse({"data": [{"b64_json": IMAGE_B64}]})


@app.post("/v1/audio/speech")
async def speech():
    # 一段 0.4 秒的静音 MP3 帧不保证可解码；联调只验证文件落盘与播放器出现。
    return Response(b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * 2048, media_type="audio/mpeg")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5196, log_level="warning")
