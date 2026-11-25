from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "test.db",
        admin_username="admin",
        admin_password="admin-pass",
        demo_user_enabled=True,
        demo_username="demo",
        demo_password="demo-pass",
        cookie_secure=False,
        llm_api_key="",
        max_upload_mb=4,
        rate_limit_per_minute=100,
    )


@pytest.fixture()
def client(settings: Settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture()
def guest(client: TestClient) -> TestClient:
    response = client.post("/api/auth/guest", json={"adultConfirmed": True})
    assert response.status_code == 200, response.text
    return client


@pytest.fixture()
def image_bytes() -> bytes:
    image = Image.new("RGB", (320, 420), (40, 30, 24))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=80)
    return buffer.getvalue()


def open_persona(client: TestClient, persona_id: str = "chloe-miller") -> dict:
    response = client.post(f"/api/personas/{persona_id}/open")
    assert response.status_code == 200, response.text
    return response.json()


def read_stream(response) -> list[dict]:
    import json

    events = []
    for line in response.iter_lines():
        if not line:
            continue
        event = json.loads(line)
        if event.get("type") != "ping":
            events.append(event)
    return events
