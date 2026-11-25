"""PLOT18 · AI 陪伴聊天 API。"""

from __future__ import annotations

import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT, Settings
from .db import Database
from .errors import AppError
from .routers import admin, auth, chat, files, personas
from .security import RateLimiter, create_user
from .services.llm import LLMClient
from .services.media import MediaStore
from .services.personas import seed_defaults
from .services.studio import Studio

DIST = ROOT / "frontend" / "dist"


async def _ensure_accounts(db: Database, settings: Settings) -> None:
    if not await db.fetchone("SELECT id FROM users WHERE username = ?", (settings.admin_username.lower(),)):
        await create_user(db, username=settings.admin_username, password=settings.admin_password,
                          display_name="主理人", role="admin", adult=True)
    if settings.demo_user_enabled and not await db.fetchone(
            "SELECT id FROM users WHERE username = ?", (settings.demo_username.lower(),)):
        await create_user(db, username=settings.demo_username, password=settings.demo_password,
                          display_name="夜归人", role="user", adult=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = app.state.settings_override or Settings.from_env()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db = Database(settings.db_path)
    await db.open()
    await seed_defaults(db)
    await _ensure_accounts(db, settings)
    await db.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (datetime.now(UTC).isoformat(),))
    http = httpx.AsyncClient(trust_env=False, timeout=120, limits=httpx.Limits(max_connections=30))
    media = MediaStore(db, settings.data_dir, settings.max_upload_mb)
    app.state.settings = settings
    app.state.db = db
    app.state.http = http
    app.state.media = media
    app.state.studio = Studio(settings, media, http)
    app.state.llm = LLMClient(settings)
    app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute)
    from .routers.chat import ActiveRuns

    app.state.active_chat_runs = ActiveRuns()
    try:
        yield
    finally:
        await http.aclose()
        await db.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="PLOT18 API", version="0.1.0", lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.settings_override = settings

    settings = settings or Settings.from_env()
    if settings.public_origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[settings.public_origin],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type"],
        )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, error: AppError):
        return JSONResponse(
            {"error": {"message": str(error), "code": error.code, "requestId": getattr(request.state, "request_id", "")}},
            status_code=error.status,
            headers={"Cache-Control": "no-store"},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, error: RequestValidationError):
        message = "；".join(f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in error.errors()[:4])
        return JSONResponse(
            {"error": {"message": message or "请求参数不正确。", "code": "VALIDATION_ERROR",
                       "requestId": getattr(request.state, "request_id", "")}},
            status_code=400,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, error: Exception):
        traceback.print_exc()
        return JSONResponse(
            {"error": {"message": "服务刚才走神了，请稍后再试。", "code": "INTERNAL_ERROR",
                       "requestId": getattr(request.state, "request_id", "")}},
            status_code=500,
        )

    app.include_router(auth.router)
    app.include_router(personas.router)
    app.include_router(chat.router)
    app.include_router(files.router)
    app.include_router(admin.router)

    @app.get("/api/health", tags=["状态"])
    async def health():
        return {"ready": True, "app": "plot18"}

    if DIST.exists():
        assets = DIST / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str):
            if path.startswith("api/"):
                return JSONResponse({"error": {"message": "接口不存在。"}}, status_code=404)
            target = (DIST / path).resolve()
            if DIST.resolve() in target.parents and target.is_file():
                return FileResponse(target)
            return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})
    else:
        @app.get("/", include_in_schema=False)
        async def root():
            return JSONResponse({
                "app": "PLOT18 API",
                "hint": "前端尚未构建。开发时运行 npm --prefix frontend run dev，或先执行构建。",
                "docs": "/api/docs",
            })

    return app


app = create_app()
