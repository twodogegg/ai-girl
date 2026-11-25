"""可被 API 转换成统一 JSON 错误的业务异常。"""

from __future__ import annotations


class AppError(Exception):
    def __init__(self, message: str, status: int = 400, *, code: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
