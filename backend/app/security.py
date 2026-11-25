"""认证与限流。

- 密码 Argon2id；会话令牌只把 SHA-256 摘要落库，Cookie 里放原令牌（httpOnly）。
- 聊天接口要求成年确认（adult_confirmed_at），人设浏览不需要登录。
- 限流是单进程内存版，够单机使用；多实例部署时换成 Redis。
"""

from __future__ import annotations

import hashlib
import re
import secrets
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, Request

from .config import Settings
from .db import Database, now
from .errors import AppError

COOKIE_NAME = "plot18_session"
_hasher = PasswordHasher()
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_\-]{3,24}$")


class AuthError(AppError):
    def __init__(self, message: str, status: int = 401) -> None:
        super().__init__(message, status, code="AUTH_REQUIRED")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        return _hasher.verify(encoded, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_user_id() -> str:
    return secrets.token_hex(12)


def valid_username(username: str) -> bool:
    return bool(USERNAME_RE.fullmatch(username))


async def create_session(db: Database, settings: Settings, user_id: str) -> str:
    token = secrets.token_urlsafe(36)
    created = datetime.now(UTC)
    expires = created + timedelta(days=settings.session_days)
    await db.execute(
        "INSERT INTO auth_sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token_digest(token), user_id, created.isoformat(), expires.isoformat()),
    )
    return token


async def destroy_session(db: Database, token: str) -> None:
    await db.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_digest(token),))


async def user_from_request(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    db: Database = request.app.state.db
    row = await db.fetchone(
        """SELECT u.* FROM auth_sessions s JOIN users u ON u.id = s.user_id
           WHERE s.token_hash = ? AND s.expires_at > ?""",
        (token_digest(token), datetime.now(UTC).isoformat()),
    )
    if row is None or row.get("disabled"):
        return None
    return row


async def current_user(request: Request) -> dict:
    user = await user_from_request(request)
    if user is None:
        raise AuthError("请先登录。", 401)
    return user


async def adult_user(user: dict = Depends(current_user)) -> dict:
    if not user.get("adult_confirmed_at"):
        raise AuthError("请先确认你已年满 18 周岁。", 403)
    return user


async def admin_user(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "admin":
        raise AuthError("需要管理员权限。", 403)
    return user


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "displayName": user["display_name"],
        "role": user["role"],
        "adultConfirmed": bool(user.get("adult_confirmed_at")),
        "createdAt": user["created_at"],
    }


def set_session_cookie(response, settings: Settings, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.session_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


class RateLimiter:
    """每个用户每分钟的消息次数限制。"""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        import time

        current = time.monotonic()
        events = self._events[key]
        while events and current - events[0] > 60:
            events.popleft()
        if len(events) >= self.limit:
            return False
        events.append(current)
        return True


async def record_adult_confirmation(db: Database, user_id: str) -> None:
    await db.execute("UPDATE users SET adult_confirmed_at = ? WHERE id = ? AND adult_confirmed_at IS NULL", (now(), user_id))


async def create_user(db: Database, *, username: str, password: str | None, display_name: str,
                      role: str = "user", adult: bool = False) -> dict:
    user_id = new_user_id()
    created = now()
    await db.execute(
        """INSERT INTO users (id, username, display_name, password_hash, role, disabled, adult_confirmed_at, created_at)
           VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
        (user_id, username.strip().lower(), display_name.strip() or username, hash_password(password) if password else None,
         role, created if adult else None, created),
    )
    user = await db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
    assert user is not None
    return user
