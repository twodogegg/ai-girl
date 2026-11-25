"""OpenAI Chat Completions 兼容的流式客户端。"""

from __future__ import annotations

from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from ..config import Settings


class LLMNotConfigured(Exception):
    pass


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: AsyncOpenAI | None = None
        if settings.llm_api_key:
            self._client = AsyncOpenAI(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                timeout=settings.llm_timeout,
                max_retries=1,
            )

    @property
    def ready(self) -> bool:
        return self._client is not None and not self.settings.demo_mode

    async def stream(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None,
                     temperature: float = 0.85, max_tokens: int = 600,
                     model: str | None = None) -> AsyncIterator[Any]:
        if self._client is None:
            raise LLMNotConfigured("还没有配置文本模型。")
        kwargs: dict[str, Any] = {
            "model": model or self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        stream = await self._client.chat.completions.create(**kwargs)
        async for chunk in stream:
            yield chunk
