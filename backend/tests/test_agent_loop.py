from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from tests.conftest import open_persona, read_stream


def chunk(content=None, tool_calls=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


class FakeLLM:
    ready = True

    def __init__(self, tool_name: str, arguments: dict):
        self.tool_name = tool_name
        self.arguments = arguments
        self.calls = 0

    async def stream(self, messages, **kwargs):
        self.calls += 1
        if self.calls == 1:
            call = SimpleNamespace(
                index=0, id="call_test",
                function=SimpleNamespace(name=self.tool_name, arguments=json.dumps(self.arguments, ensure_ascii=False)),
            )
            yield chunk(None, [call])
        else:
            yield chunk("我记住了，下次会先问你今天发生了什么。", None)


class FakeStudio:
    def __init__(self, file_id: str):
        self.file_id = file_id

    async def selfie(self, persona, *, scene, outfit, caption, owner):
        return {"fileId": self.file_id, "url": f"/api/files/{self.file_id}", "caption": caption}

    async def voice(self, text, *, voice, owner):
        return {"fileId": self.file_id, "url": f"/api/files/{self.file_id}", "text": text}


def _chat(client: TestClient, conversation_id: str, text: str) -> list[dict]:
    with client.stream("POST", "/api/chat", json={
        "personaId": "chloe-miller", "conversationId": conversation_id, "text": text,
    }) as response:
        assert response.status_code == 200, response.text
        return read_stream(response)


def test_llm_tool_loop_remembers(client: TestClient):
    client.app.state.llm = FakeLLM("remember", {"content": "他今天很累，喜欢海边", "kind": "fact", "importance": 4})
    assert client.post("/api/auth/guest", json={"adultConfirmed": True}).status_code == 200
    data = open_persona(client)
    events = _chat(client, data["conversation"]["id"], "我今天很累，喜欢海边")

    tool_events = [event for event in events if event["type"] == "tool"]
    assert tool_events[0]["status"] == "running"
    assert tool_events[-1]["status"] == "success"
    done = events[-1]
    assert done["type"] == "done"
    assert done["demo"] is False
    assert "记住了" in done["message"]["content"]
    memories = client.get(f"/api/conversations/{data['conversation']['id']}/memories").json()["memories"]
    assert any("喜欢海边" in item["content"] for item in memories)


def test_llm_photo_tool_emits_image(client: TestClient, image_bytes: bytes):
    client.app.state.llm = FakeLLM("send_photo", {
        "scene": "在窗边", "outfit": "白衬衫", "caption": "喏，刚拍的。",
    })
    assert client.post("/api/auth/guest", json={"adultConfirmed": True}).status_code == 200
    upload = client.post("/api/files", files={"file": ("photo.jpg", image_bytes, "image/jpeg")})
    assert upload.status_code == 200, upload.text
    saved = upload.json()
    client.app.state.studio = FakeStudio(saved["id"])
    data = open_persona(client)
    events = _chat(client, data["conversation"]["id"], "给我看看你")

    images = [event for event in events if event["type"] == "image"]
    assert images and images[0]["fileId"] == saved["id"]
    done = events[-1]
    parts = done["message"]["parts"]
    assert any(part["type"] == "image" and part["fileId"] == saved["id"] for part in parts)


def test_llm_activate_skill(client: TestClient):
    client.app.state.llm = FakeLLM("activate_skill", {"skillId": "late-night-talk"})
    assert client.post("/api/auth/guest", json={"adultConfirmed": True}).status_code == 200
    data = open_persona(client)
    events = _chat(client, data["conversation"]["id"], "用深夜慢聊的方式陪我")
    tool = [event for event in events if event["type"] == "tool"][-1]
    assert tool["status"] == "success"
    assert "深夜" in tool["summary"]
    done = events[-1]
    assert done["type"] == "done"
    assert "记住了" in done["message"]["content"]
