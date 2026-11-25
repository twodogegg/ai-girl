"""运行时配置。所有密钥只从环境变量读取，不进入前端。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    db_path: Path
    # 监听地址：127.0.0.1 仅本机；0.0.0.0 允许局域网访问。
    host: str = "127.0.0.1"
    port: int = 5190
    admin_username: str = "admin"
    admin_password: str = "change-me-now"
    demo_username: str = "demo"
    demo_password: str = "demo1234"
    demo_user_enabled: bool = True
    session_days: int = 30
    cookie_secure: bool = False
    public_origin: str = ""
    # 文本模型：任何 OpenAI Chat Completions 兼容网关。
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-5-5"
    llm_vision: bool = True
    llm_timeout: int = 120
    demo_mode: bool = False
    # 生图 / 语音：未配置时工具会礼貌地返回不可用，不影响文字聊天。
    image_base_url: str = ""
    image_api_key: str = ""
    image_model: str = "gpt-image-2"
    image_size: str = "1024x1536"
    tts_base_url: str = ""
    tts_api_key: str = ""
    tts_model: str = "gpt-4o-mini-tts"
    tts_voice: str = "alloy"
    max_upload_mb: int = 8
    max_context_messages: int = 48
    max_tool_rounds: int = 6
    rate_limit_per_minute: int = 24

    @property
    def images_enabled(self) -> bool:
        return bool(self.image_base_url and self.image_api_key)

    @property
    def tts_enabled(self) -> bool:
        return bool(self.tts_base_url and self.tts_api_key)

    @property
    def llm_ready(self) -> bool:
        return bool(self.llm_api_key) and not self.demo_mode

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(_env("DATA_DIR", str(ROOT / "data"))).expanduser()
        return cls(
            data_dir=data_dir,
            db_path=Path(_env("DATABASE_PATH", str(data_dir / "ai-girl.db"))).expanduser(),
            host=_env("HOST", "127.0.0.1"),
            port=_int("PORT", 5190),
            admin_username=_env("ADMIN_USERNAME", "admin"),
            admin_password=_env("ADMIN_PASSWORD", "change-me-now"),
            demo_username=_env("DEMO_USERNAME", "demo"),
            demo_password=_env("DEMO_PASSWORD", "demo1234"),
            demo_user_enabled=_bool("DEMO_USER_ENABLED", True),
            session_days=_int("SESSION_DAYS", 30),
            cookie_secure=_bool("COOKIE_SECURE", False),
            public_origin=_env("PUBLIC_ORIGIN", ""),
            llm_base_url=_env("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            llm_api_key=_env("LLM_API_KEY", ""),
            llm_model=_env("LLM_MODEL", "claude-sonnet-5-5"),
            llm_vision=_bool("LLM_VISION", True),
            llm_timeout=_int("LLM_TIMEOUT", 120),
            demo_mode=_bool("DEMO_MODE", False),
            image_base_url=_env("IMAGE_BASE_URL", "").rstrip("/"),
            image_api_key=_env("IMAGE_API_KEY", ""),
            image_model=_env("IMAGE_MODEL", "gpt-image-2"),
            image_size=_env("IMAGE_SIZE", "1024x1536"),
            tts_base_url=_env("TTS_BASE_URL", "").rstrip("/"),
            tts_api_key=_env("TTS_API_KEY", ""),
            tts_model=_env("TTS_MODEL", "gpt-4o-mini-tts"),
            tts_voice=_env("TTS_VOICE", "alloy"),
            max_upload_mb=_int("MAX_UPLOAD_MB", 8),
            max_context_messages=_int("MAX_CONTEXT_MESSAGES", 48),
            max_tool_rounds=_int("MAX_TOOL_ROUNDS", 6),
            rate_limit_per_minute=_int("RATE_LIMIT_PER_MINUTE", 24),
        )
