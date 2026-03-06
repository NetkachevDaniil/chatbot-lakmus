from __future__ import annotations

import random
import time
from threading import Thread
from typing import Optional

from ..models import Chat, PendingRequest
from ..repository import InMemoryRepository
from .auth import ServiceEndpoints


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
        welcome = self.repository.create_chat(user_id, title="Новый чат")
        self.repository.add_message(
            user_id,
            welcome.id,
            "assistant",
            (
                "Загрузите файл, добавьте prompt и отправьте запрос. "
                "Ответ от mock `сервиса б` появится автоматически."
            ),
        )
        return welcome

    async def create_chat(self, user_id: str) -> Chat:
        chat = self.repository.create_chat(user_id)
        self.repository.add_message(
            user_id,
            chat.id,
            "assistant",
            "Новый диалог создан. Опишите задачу и при необходимости приложите файл.",
        )
        return chat

    async def get_chat(self, user_id: str, chat_id: str) -> Optional[Chat]:
        return self.repository.get_chat(user_id, chat_id)

    async def submit(
        self,
        user_id: str,
        chat_id: str,
        prompt: str,
        file_name: Optional[str],
    ) -> PendingRequest:
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
            "Запрос отправлен в `сервис а`. Ожидание ответа от `сервиса б`...",
            status="pending",
            meta={"stage": "submitted"},
        )
        pending = self.repository.create_request(user_id, chat_id, assistant_message.id)
        Thread(
            target=self._complete_request,
            args=(pending.id, prompt, file_name),
            daemon=True,
        ).start()
        return pending

    async def get_request(self, request_id: str) -> Optional[PendingRequest]:
        return self.repository.get_request(request_id)

    def _complete_request(self, request_id: str, prompt: str, file_name: Optional[str]) -> None:
        time.sleep(random.uniform(1.4, 2.8))
        request = self.repository.get_request(request_id)
        if request is None:
            return
        payload = self._build_mock_result(prompt=prompt, file_name=file_name)
        self.repository.complete_request(request_id, payload)

    def _build_mock_result(self, prompt: str, file_name: Optional[str]) -> dict:
        topic = "табличным данным" if file_name else "текстовому запросу"
        file_hint = file_name or "файл не прикреплен"
        normalized_prompt = " ".join(prompt.split())
        excerpt = normalized_prompt[:120] or "Без текста запроса"
        insights = [
            "Структура входных данных распознана и подготовлена к обработке.",
            "Ответ оформлен как JSON, пригодный для дальнейшего рендера на фронте.",
            "Интеграцию с реальными сервисами можно заменить в service layer без переделки UI.",
        ]
        return {
            "summary": (
                f"Ответ от `сервиса б` получен. Обработан запрос по {topic}; "
                f"источник: {file_hint}."
            ),
            "request_echo": excerpt,
            "detected_input": {
                "file_name": file_name,
                "mode": "file+prompt" if file_name else "prompt-only",
            },
            "analysis": {
                "status": "ready",
                "confidence": 0.94,
                "observations": insights,
            },
            "recommended_next_steps": [
                "Проверить JSON на клиенте и отрендерить итоговые карточки.",
                "Подменить mock URL реальными endpoint сервисов.",
                "Добавить хранение истории в БД вместо in-memory состояния.",
            ],
        }
