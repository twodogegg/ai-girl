"""生图与语音：OpenAI 兼容接口。未配置时抛 ToolUnavailable，由工具层转成温和的提示。"""

from __future__ import annotations

import httpx

from ..config import Settings
from .media import MediaStore


class ToolUnavailable(Exception):
    pass


class Studio:
    def __init__(self, settings: Settings, media: MediaStore, http: httpx.AsyncClient) -> None:
        self.settings = settings
        self.media = media
        self.http = http

    async def selfie(self, persona: dict, *, scene: str, outfit: str, caption: str, owner: str) -> dict:
        if not self.settings.images_enabled:
            raise ToolUnavailable("自拍服务还没有配置。")
        identity = (
            f"{persona.get('name')}, a fictional {persona.get('age')}-year-old adult woman, "
            f"{persona.get('occupation')} in {persona.get('city')}. Personality: {persona.get('personality')}"
        )
        prompt = (
            f"Tasteful cinematic phone selfie of {identity}. Scene: {scene}. Wearing: {outfit or 'everyday clothes'}. "
            "Adult subject, natural skin texture, warm low light, 35mm film grain, shallow depth of field, "
            "candid and intimate but not explicit, no nudity, no text, no watermark. Vertical 3:4 framing."
        )
        body = {
            "model": self.settings.image_model,
            "prompt": prompt,
            "n": 1,
            "size": self.settings.image_size,
            "response_format": "b64_json",
        }
        try:
            response = await self.http.post(
                f"{self.settings.image_base_url}/images/generations",
                headers={"Authorization": f"Bearer {self.settings.image_api_key}"},
                json=body,
                timeout=120,
            )
        except httpx.HTTPError as error:
            raise ToolUnavailable("自拍服务连接失败，过一会儿再试。") from error
        if response.status_code >= 400:
            raise ToolUnavailable("自拍服务暂时不可用。")
        payload = response.json()
        item = (payload.get("data") or [{}])[0]
        encoded = item.get("b64_json")
        if encoded:
            record = await self.media.save_image_from_b64(encoded, owner, "persona-selfie")
        elif item.get("url"):
            try:
                image = await self.http.get(item["url"], timeout=120)
                image.raise_for_status()
            except httpx.HTTPError as error:
                raise ToolUnavailable("自拍图片下载失败。") from error
            record = await self.media.save_image_from_url(image.content, owner, "persona-selfie")
        else:
            raise ToolUnavailable("自拍服务没有返回图片。")
        return {"fileId": record["id"], "url": f"/api/files/{record['id']}", "caption": caption}

    async def voice(self, text: str, *, voice: str, owner: str) -> dict:
        if not self.settings.tts_enabled:
            raise ToolUnavailable("语音服务还没有配置。")
        spoken = " ".join(str(text or "").split()).strip()[:400]
        if not spoken:
            raise ToolUnavailable("没有可朗读的内容。")
        body = {
            "model": self.settings.tts_model,
            "voice": voice or self.settings.tts_voice,
            "input": spoken,
            "response_format": "mp3",
        }
        try:
            response = await self.http.post(
                f"{self.settings.tts_base_url}/audio/speech",
                headers={"Authorization": f"Bearer {self.settings.tts_api_key}", "Content-Type": "application/json"},
                json=body,
                timeout=90,
            )
        except httpx.HTTPError as error:
            raise ToolUnavailable("语音服务连接失败。") from error
        if response.status_code >= 400:
            raise ToolUnavailable("语音服务暂时不可用。")
        record = await self.media.save_audio(response.content, owner, "persona-voice")
        return {"fileId": record["id"], "url": f"/api/files/{record['id']}", "text": spoken}
