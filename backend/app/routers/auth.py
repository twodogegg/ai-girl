"""注册 / 登录 / 访客 / 成年确认。"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from ..config import Settings
from ..db import Database
from ..errors import AppError
from ..security import (
    AuthError,
    adult_user,
    clear_session_cookie,
    create_session,
    create_user,
    current_user,
    destroy_session,
    public_user,
    record_adult_confirmation,
    set_session_cookie,
    valid_username,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


class RegisterInput(BaseModel):
    username: str = Field(min_length=3, max_length=24)
    password: str = Field(min_length=6, max_length=128)
    displayName: str = Field(default="", max_length=24)
    adultConfirmed: bool = False


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class GuestInput(BaseModel):
    adultConfirmed: bool = False


def _db(request: Request) -> Database:
    return request.app.state.db


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@router.post("/register")
async def register(data: RegisterInput, request: Request, response: Response):
    if not valid_username(data.username):
        raise AppError("用户名只能包含字母、数字、下划线或短横线，长度 3–24。", 400)
    if not data.adultConfirmed:
        raise AppError("请先确认你已年满 18 周岁。", 403)
    db = _db(request)
    existing = await db.fetchone("SELECT id FROM users WHERE username = ?", (data.username.strip().lower(),))
    if existing:
        raise AppError("这个用户名已经被使用了。", 409)
    user = await create_user(db, username=data.username, password=data.password,
                             display_name=data.displayName or data.username, adult=True)
    token = await create_session(db, _settings(request), user["id"])
    set_session_cookie(response, _settings(request), token)
    return {"user": public_user(user)}


@router.post("/login")
async def login(data: LoginInput, request: Request, response: Response):
    db = _db(request)
    user = await db.fetchone("SELECT * FROM users WHERE username = ?", (data.username.strip().lower(),))
    if user is None or user.get("disabled") or not verify_password(data.password, user.get("password_hash")):
        raise AuthError("用户名或密码不正确。", 401)
    token = await create_session(db, _settings(request), user["id"])
    set_session_cookie(response, _settings(request), token)
    return {"user": public_user(user)}


@router.post("/guest")
async def guest(data: GuestInput, request: Request, response: Response):
    if not data.adultConfirmed:
        raise AppError("请先确认你已年满 18 周岁。", 403)
    db = _db(request)
    username = f"guest_{secrets.token_hex(4)}"
    user = await create_user(db, username=username, password=None, display_name="夜归人", adult=True)
    token = await create_session(db, _settings(request), user["id"])
    set_session_cookie(response, _settings(request), token)
    return {"user": public_user(user)}


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("plot18_session")
    if token:
        await destroy_session(_db(request), token)
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
async def me(request: Request):
    from ..security import user_from_request

    user = await user_from_request(request)
    return {"user": public_user(user) if user else None}


@router.post("/adult-confirm")
async def adult_confirm(request: Request, user: dict = Depends(current_user)):
    await record_adult_confirmation(_db(request), user["id"])
    refreshed = await _db(request).fetchone("SELECT * FROM users WHERE id = ?", (user["id"],))
    return {"user": public_user(refreshed or user)}


@router.get("/session-check")
async def session_check(user: dict = Depends(adult_user)):
    return {"ok": True, "user": public_user(user)}
