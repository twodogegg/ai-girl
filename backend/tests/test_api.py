from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import open_persona, read_stream


def test_health_and_public_personas(client: TestClient):
    assert client.get("/api/health").json()["ready"] is True
    payload = client.get("/api/personas").json()
    assert len(payload["personas"]) >= 10
    first = payload["personas"][0]
    assert first["age"] >= 18
    assert "toolIds" not in first
    assert "promptExtra" not in first
    assert "skillIds" not in first


def test_adult_confirmation_required(client: TestClient):
    assert client.post("/api/auth/guest", json={"adultConfirmed": False}).status_code == 403
    assert client.post("/api/auth/register", json={
        "username": "nightowl", "password": "secret123", "displayName": "夜猫", "adultConfirmed": False,
    }).status_code == 403
    assert client.post("/api/auth/register", json={
        "username": "nightowl", "password": "secret123", "displayName": "夜猫", "adultConfirmed": True,
    }).status_code == 200
    me = client.get("/api/auth/me").json()["user"]
    assert me["adultConfirmed"] is True


def test_open_persona_creates_greeting_and_chat_streams(guest: TestClient):
    data = open_persona(guest)
    assert data["conversation"]["personaId"] == "chloe-miller"
    assert len(data["messages"]) == 1
    assert data["messages"][0]["role"] == "assistant"
    assert "克洛伊" not in data["messages"][0]["content"]

    with guest.stream("POST", "/api/chat", json={
        "personaId": "chloe-miller",
        "conversationId": data["conversation"]["id"],
        "text": "今天有点累，不过看到你消息好多了。",
    }) as response:
        assert response.status_code == 200
        events = read_stream(response)

    types = [event["type"] for event in events]
    assert types[0] == "meta"
    assert "text" in types
    assert types[-1] == "done"
    done = events[-1]
    assert done["message"]["role"] == "assistant"
    assert done["message"]["content"]
    assert "tools" in done["message"]["meta"]


def test_chat_requires_conversation_ownership(client: TestClient):
    assert client.post("/api/auth/guest", json={"adultConfirmed": True}).status_code == 200
    data = open_persona(client)
    client.cookies.clear()
    assert client.post("/api/auth/guest", json={"adultConfirmed": True}).status_code == 200
    response = client.post("/api/chat", json={
        "personaId": "chloe-miller", "conversationId": data["conversation"]["id"], "text": "hi",
    })
    assert response.status_code == 404


def test_upload_and_private_file_access(guest: TestClient, image_bytes: bytes):
    response = guest.post("/api/files", files={"file": ("photo.jpg", image_bytes, "image/jpeg")})
    assert response.status_code == 200, response.text
    file_id = response.json()["id"]
    assert guest.get(f"/api/files/{file_id}").status_code == 200

    guest.cookies.clear()
    assert guest.post("/api/auth/guest", json={"adultConfirmed": True}).status_code == 200
    assert guest.get(f"/api/files/{file_id}").status_code == 404


def test_admin_can_edit_persona_but_users_cannot(guest: TestClient):
    assert guest.get("/api/admin/personas").status_code == 403

    guest.cookies.clear()
    login = guest.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    assert login.status_code == 200
    personas = guest.get("/api/admin/personas").json()["personas"]
    chloe = next(item for item in personas if item["id"] == "chloe-miller")
    assert chloe["published"] is True
    assert "remember" in chloe["toolIds"]

    chloe["tagline"] = "改过的介绍"
    chloe["toolIds"] = ["remember", "get_time"]
    response = guest.put("/api/admin/personas/chloe-miller", json=chloe)
    assert response.status_code == 200, response.text
    saved = response.json()["persona"]
    assert saved["tagline"] == "改过的介绍"
    assert saved["toolIds"] == ["remember", "get_time"]

    public = guest.get("/api/personas/chloe-miller").json()["persona"]
    assert public["tagline"] == "改过的介绍"
    assert "toolIds" not in public


def test_admin_skill_crud(guest: TestClient):
    guest.cookies.clear()
    guest.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    created = guest.post("/api/admin/skills", json={
        "name": "测试 Skill", "description": "只在测试里用", "category": "测试",
        "instructions": "- 每次回复只写一句。", "alwaysOn": False,
    })
    assert created.status_code == 200, created.text
    skill = created.json()["skill"]
    assert skill["id"]
    listed = guest.get("/api/admin/skills").json()["skills"]
    assert any(item["id"] == skill["id"] for item in listed)
    assert guest.delete(f"/api/admin/skills/{skill['id']}").status_code == 200
    assert not any(item["id"] == skill["id"] for item in guest.get("/api/admin/skills").json()["skills"])


def test_memory_api(guest: TestClient):
    data = open_persona(guest, "lin-mei")
    # 演示引擎在包含“我”的陈述句上会调用 remember。
    with guest.stream("POST", "/api/chat", json={
        "personaId": "lin-mei", "conversationId": data["conversation"]["id"],
        "text": "我养了一只叫年糕的橘猫，我很喜欢它。",
    }) as response:
        read_stream(response)
    memories = guest.get(f"/api/conversations/{data['conversation']['id']}/memories").json()["memories"]
    assert any("年糕" in item["content"] for item in memories)
    first = memories[0]
    assert guest.delete(f"/api/memories/{first['id']}").status_code == 200
