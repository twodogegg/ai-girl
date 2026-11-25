"""用户图片上传与私有文件读取。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse

from ..errors import AppError
from ..security import adult_user
from ..services.media import MediaError

router = APIRouter(prefix="/api/files", tags=["文件"])


@router.post("")
async def upload(request: Request, file: UploadFile = File(...), user: dict = Depends(adult_user)):
    settings = request.app.state.settings
    media = request.app.state.media
    raw = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise AppError(f"图片不能超过 {settings.max_upload_mb} MB。", 413)
    if not raw:
        raise AppError("没有收到图片。", 400)
    mime = (file.content_type or "").lower()
    try:
        record = await media.save_user_image(raw, mime, user["id"])
    except MediaError:
        raise
    return {
        "id": record["id"],
        "url": f"/api/files/{record['id']}",
        "mime": record["mime"],
        "width": record["width"],
        "height": record["height"],
        "size": record["size"],
    }


@router.get("/{file_id}")
async def read_file(file_id: str, request: Request, user: dict = Depends(adult_user)):
    record = await request.app.state.media.get(file_id)
    if record is None or record.get("owner_user_id") != user["id"]:
        raise AppError("文件不存在。", 404)
    path = request.app.state.media.path_of(record)
    if not path.exists():
        raise AppError("文件不存在。", 404)
    return FileResponse(
        path,
        media_type=record["mime"],
        headers={
            "Cache-Control": "private, max-age=86400",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )
