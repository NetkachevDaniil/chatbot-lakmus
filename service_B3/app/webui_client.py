from __future__ import annotations

from urllib.parse import urljoin

import httpx

from app.config import settings


class WebUIClient:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def send_response(self, user_id: str, chat_id: str, payload: dict) -> None:
        path = settings.webui.response_path_template.format(user_id=user_id, chat_id=chat_id)
        url = urljoin(settings.webui.base_url.rstrip("/") + "/", path.lstrip("/"))
        response = await self.client.post(url, json=payload)
        response.raise_for_status()

    async def aclose(self) -> None:
        await self.client.aclose()
