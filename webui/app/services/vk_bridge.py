from __future__ import annotations

import asyncio

from ..config import Settings
from .vk_bot import VkApiClient, VkBotSettings


class VkBridgeService:
    def __init__(self, settings: Settings) -> None:
        self.bot_settings = VkBotSettings.from_app_settings(settings)

    def is_configured(self) -> bool:
        return self.bot_settings.group_id > 0 and bool(self.bot_settings.access_token.strip())

    async def send_message(self, peer_id: int, text: str) -> None:
        if not self.is_configured():
            raise RuntimeError("VK bot settings are not configured")

        api_client = VkApiClient(self.bot_settings)
        await asyncio.to_thread(api_client.send_message, peer_id=peer_id, text=text)
