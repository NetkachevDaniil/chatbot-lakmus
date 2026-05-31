from __future__ import annotations

from typing import Optional

import httpx
from fastapi import UploadFile

from ..models import Chat, PendingRequest, ServiceResponse
from ..repository import DEFAULT_CHAT_TITLE, InMemoryRepository
from .auth import ServiceEndpoints


WELCOME_MESSAGE = (
    "Я Лакмус. Загрузите файл, добавьте запрос, и я отправлю его в сервис А, "
    "а затем покажу результат, когда сервис Б вернет ответ."
)
NEW_CHAT_MESSAGE = (
    "Новый диалог создан. Отправьте файл и промпт, чтобы сформировать запрос для сервиса А."
)
PENDING_MESSAGE = "Запрос отправлен в сервис А. Ожидание ответа от сервиса Б..."
SERVICE_A_ERROR = "Не удалось отправить запрос в сервис А."
FILE_REQUIRED_ERROR = "Сейчас для отправки в сервис А нужно прикрепить файл."
ACTIVE_REQUEST_ERROR = (
    "В этом чате уже есть незавершенный запрос. Дождитесь ответа сервиса Б."
)


class MockChatService:
    def __init__(self, repository: InMemoryRepository, endpoints: ServiceEndpoints) -> None:
        self.repository = repository
        self.endpoints = endpoints

    async def list_chats(self, user_id: str) -> list[Chat]:
        return self.repository.list_chats(user_id)

    async def get_or_create_default_chat(self, user_id: str) -> Chat:
        chats = self.repository.list_chats(user_id)
        if chats:
            return chats[0]
        welcome = self.repository.create_chat(user_id, title=DEFAULT_CHAT_TITLE)
        self.repository.add_message(user_id, welcome.id, "assistant", WELCOME_MESSAGE)
        return welcome

    async def create_chat(
        self,
        user_id: str,
        *,
        title: Optional[str] = None,
        assistant_message: Optional[str] = NEW_CHAT_MESSAGE,
    ) -> Chat:
        chat = self.repository.create_chat(user_id, title=title)
        if assistant_message:
            self.repository.add_message(user_id, chat.id, "assistant", assistant_message)
        return chat

    async def get_chat(self, user_id: str, chat_id: str) -> Optional[Chat]:
        return self.repository.get_chat(user_id, chat_id)

    async def delete_chat(self, user_id: str, chat_id: str) -> bool:
        return self.repository.delete_chat(user_id, chat_id)

    async def submit(
        self,
        user_id: str,
        chat_id: str,
        prompt: str,
        file: Optional[UploadFile],
        *,
        request_meta: Optional[dict] = None,
    ) -> PendingRequest:
        active_request = self.repository.get_active_request(user_id, chat_id)
        if active_request is not None:
            raise ValueError(ACTIVE_REQUEST_ERROR)
        if file is None or not file.filename:
            raise ValueError(FILE_REQUIRED_ERROR)

        file_name = file.filename
        self.repository.add_message(
            user_id,
            chat_id,
            "user",
            prompt,
            file_name=file_name,
        )
        assistant_message = self.repository.add_message(
            user_id,
            chat_id,
            "assistant",
            PENDING_MESSAGE,
            status="pending",
            meta={"stage": "submitted", **(request_meta or {})},
        )
        pending = self.repository.create_request(
            user_id,
            chat_id,
            assistant_message.id,
            meta=request_meta,
        )

        try:
            ack = await self._forward_to_service_a(
                user_id=user_id,
                chat_id=chat_id,
                prompt=prompt,
                file=file,
            )
        except Exception as exc:
            meta = {
                "forward_error": str(exc),
                "service_a_url": self._build_service_a_url(user_id, chat_id),
            }
            self.repository.fail_request(pending.id, SERVICE_A_ERROR, meta=meta)
            raise RuntimeError(f"{SERVICE_A_ERROR} {exc}") from exc

        self.repository.mark_request_forwarded(
            pending.id,
            meta={
                "service_a_url": self._build_service_a_url(user_id, chat_id),
                "service_a_ack": ack,
            },
        )
        return pending

    async def get_request(self, request_id: str) -> Optional[PendingRequest]:
        return self.repository.get_request(request_id)

    async def accept_response(self, payload: ServiceResponse) -> Optional[PendingRequest]:
        try:
            return self.repository.apply_response(payload)
        except KeyError:
            return None

    def _build_service_a_url(self, user_id: str, chat_id: str) -> str:
        base = self.endpoints.service_a.rstrip("/")
        return f"{base}/user/{user_id}/chat/{chat_id}/request"

    async def _forward_to_service_a(
        self,
        *,
        user_id: str,
        chat_id: str,
        prompt: str,
        file: UploadFile,
    ) -> dict:
        url = self._build_service_a_url(user_id, chat_id)
        data = {"prompt": prompt}
        content = await file.read()
        files = {
            "file": (
                file.filename,
                content,
                file.content_type or "application/octet-stream",
            )
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, data=data, files=files)
            response.raise_for_status()

        payload: dict
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw_text": response.text}

        return {
            "status_code": response.status_code,
            "payload": payload,
        }
