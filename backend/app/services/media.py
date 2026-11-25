"""图片 / 音频文件存储。

用户上传的图片统一重新编码为 JPEG：去掉 EXIF、限制边长和体积，避免把原图里的
GPS / 设备信息带给模型或静态目录。生成图与语音也走同一张 files 表。
"""

from __future__ import annotations

import base64
import hashlib
import io
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from ..db import Database, now
from ..errors import AppError

ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
MAX_SIDE = 1600
JPEG_QUALITY = 86


class MediaError(AppError):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message, status, code="MEDIA_ERROR")


class MediaStore:
    def __init__(self, db: Database, data_dir: Path, max_upload_mb: int = 8) -> None:
        self.db = db
        self.root = data_dir / "files"
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_upload_mb * 1024 * 1024

    def _record(self, file_id: str, owner: str | None, kind: str, mime: str, data: bytes,
                path: Path, width: int | None = None, height: int | None = None) -> dict[str, Any]:
        return {
            "id": file_id,
            "owner_user_id": owner,
            "kind": kind,
            "mime": mime,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "path": str(path),
            "width": width,
            "height": height,
            "created_at": now(),
        }

    async def _insert(self, record: dict[str, Any]) -> dict[str, Any]:
        await self.db.execute(
            """INSERT INTO files (id, owner_user_id, kind, mime, size, sha256, path, width, height, created_at)
               VALUES (:id, :owner_user_id, :kind, :mime, :size, :sha256, :path, :width, :height, :created_at)""",
            record,
        )
        return record

    def _normalize_image(self, data: bytes, max_side: int = MAX_SIDE) -> tuple[bytes, int, int]:
        if len(data) > self.max_bytes:
            raise MediaError(f"图片不能超过 {self.max_bytes // (1024 * 1024)} MB。", 413)
        try:
            image = Image.open(io.BytesIO(data))
            image = ImageOps.exif_transpose(image)
            image.load()
        except (UnidentifiedImageError, OSError) as error:
            raise MediaError("无法读取这张图片，请换一张 JPG / PNG / WebP。") from error
        if image.mode in {"RGBA", "LA"}:
            background = Image.new("RGB", image.size, (16, 17, 20))
            background.paste(image, mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(output, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        return output.getvalue(), image.width, image.height

    async def save_user_image(self, data: bytes, mime: str, owner: str) -> dict[str, Any]:
        if mime not in ALLOWED_IMAGE_MIME:
            raise MediaError("只支持 JPG / PNG / WebP 图片。", 415)
        normalized, width, height = self._normalize_image(data)
        return await self.save_image_bytes(normalized, owner, "user-photo", width, height)

    async def save_image_bytes(self, data: bytes, owner: str | None, kind: str,
                               width: int | None = None, height: int | None = None) -> dict[str, Any]:
        file_id = uuid.uuid4().hex
        path = self.root / f"{file_id}.jpg"
        path.write_bytes(data)
        record = self._record(file_id, owner, kind, "image/jpeg", data, path, width, height)
        return await self._insert(record)

    async def save_image_from_b64(self, encoded: str, owner: str | None, kind: str) -> dict[str, Any]:
        try:
            raw = base64.b64decode(encoded, validate=True)
        except Exception as error:
            raise MediaError("图片服务返回了无法解析的数据。", 502) from error
        normalized, width, height = self._normalize_image(raw)
        return await self.save_image_bytes(normalized, owner, kind, width, height)

    async def save_image_from_url(self, data: bytes, owner: str | None, kind: str) -> dict[str, Any]:
        normalized, width, height = self._normalize_image(data)
        return await self.save_image_bytes(normalized, owner, kind, width, height)

    async def save_audio(self, data: bytes, owner: str | None, kind: str, mime: str = "audio/mpeg") -> dict[str, Any]:
        if len(data) > 20 * 1024 * 1024:
            raise MediaError("语音文件过大。", 413)
        file_id = uuid.uuid4().hex
        path = self.root / f"{file_id}.mp3"
        path.write_bytes(data)
        record = self._record(file_id, owner, kind, mime, data, path)
        return await self._insert(record)

    async def get(self, file_id: str) -> dict[str, Any] | None:
        return await self.db.fetchone("SELECT * FROM files WHERE id = ?", (file_id,))

    def path_of(self, record: dict[str, Any]) -> Path:
        return Path(record["path"])

    def data_url(self, record: dict[str, Any], max_side: int = 1024) -> str:
        """给模型的图片统一缩到 1024 内，history 里也只传当前轮需要的图。"""
        path = self.path_of(record)
        if not path.exists():
            raise MediaError("图片已不存在，请重新上传。", 404)
        try:
            image = Image.open(path)
            image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            if image.mode != "RGB":
                image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=82, optimize=True)
            payload = buffer.getvalue()
        except Exception:
            payload = path.read_bytes()
        return "data:image/jpeg;base64," + base64.b64encode(payload).decode("ascii")

    def public_url(self, record: dict[str, Any]) -> str:
        return f"/api/files/{record['id']}"
