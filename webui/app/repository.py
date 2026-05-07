from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from .models import AuthSession, Chat, Message, PendingRequest, ServiceResponse, User, new_id


UTC = timezone.utc
DEFAULT_CHAT_TITLE = "Новый чат"


class InMemoryRepository:
    def __init__(self, access_minutes: int, refresh_days: int) -> None:
        self.access_minutes = access_minutes
        self.refresh_days = refresh_days
        self.users_by_name: dict[str, User] = {}
        self.access_tokens: dict[str, AuthSession] = {}
        self.refresh_tokens: dict[str, tuple[str, datetime]] = {}
        self.chats: dict[str, Chat] = {}
        self.requests: dict[str, PendingRequest] = {}

    def _now(self) -> datetime:
        return datetime.now(tz=UTC)

    def get_or_create_user(self, username: str) -> User:
        normalized = username.strip().lower()
        existing = self.users_by_name.get(normalized)
        if existing is not None:
            return existing

        display_name = username.strip() or "User"
        user = User(
            id=new_id("usr"),
            username=normalized,
            display_name=display_name.title(),
        )
        self.users_by_name[normalized] = user
        return user

    def create_session(self, user: User, refresh_token: Optional[str] = None) -> AuthSession:
        now = self._now()
        access_token = new_id("atk")
        if refresh_token is None:
            refresh_token = new_id("rtk")

        refresh_expires = now + timedelta(days=self.refresh_days)
        access_expires = now + timedelta(minutes=self.access_minutes)
        self.refresh_tokens[refresh_token] = (user.id, refresh_expires)

        session = AuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=access_expires,
            user=user,
        )
        self.access_tokens[access_token] = session
        return session

    def get_valid_access_session(self, access_token: Optional[str]) -> Optional[AuthSession]:
        if not access_token:
            return None
        session = self.access_tokens.get(access_token)
        if session is None:
            return None
        if session.expires_at <= self._now():
            self.access_tokens.pop(access_token, None)
            return None
        return session

    def refresh_access_session(self, refresh_token: Optional[str]) -> Optional[AuthSession]:
        if not refresh_token:
            return None

        refresh_state = self.refresh_tokens.get(refresh_token)
        if refresh_state is None:
            return None

        user_id, expires_at = refresh_state
        if expires_at <= self._now():
            self.refresh_tokens.pop(refresh_token, None)
            return None

        user = next((item for item in self.users_by_name.values() if item.id == user_id), None)
        if user is None:
            return None

        session = self.create_session(user, refresh_token=refresh_token)
        session.refreshed = True
        return session

    def revoke_session(self, access_token: Optional[str], refresh_token: Optional[str]) -> None:
        if access_token:
            self.access_tokens.pop(access_token, None)
        if refresh_token:
            self.refresh_tokens.pop(refresh_token, None)

    def list_chats(self, user_id: str) -> list[Chat]:
        chats = [chat for chat in self.chats.values() if chat.user_id == user_id]
        return sorted(chats, key=lambda item: item.updated_at, reverse=True)

    def create_chat(self, user_id: str, title: Optional[str] = None) -> Chat:
        now = self._now()
        chat = Chat(
            user_id=user_id,
            title=title or DEFAULT_CHAT_TITLE,
            created_at=now,
            updated_at=now,
        )
        self.chats[chat.id] = chat
        return chat

    def get_chat(self, user_id: str, chat_id: str) -> Optional[Chat]:
        chat = self.chats.get(chat_id)
        if chat is None or chat.user_id != user_id:
            return None
        return chat

    def delete_chat(self, user_id: str, chat_id: str) -> bool:
        chat = self.get_chat(user_id, chat_id)
        if chat is None:
            return False

        self.chats.pop(chat_id, None)
        request_ids = [
            request_id
            for request_id, request in self.requests.items()
            if request.chat_id == chat_id
        ]
        for request_id in request_ids:
            self.requests.pop(request_id, None)
        return True

    def add_message(
        self,
        user_id: str,
        chat_id: str,
        role: str,
        content: str,
        *,
        file_name: Optional[str] = None,
        status: str = "done",
        meta: Optional[dict] = None,
    ) -> Message:
        chat = self.get_chat(user_id, chat_id)
        if chat is None:
            raise KeyError(f"Chat {chat_id} not found")

        message = Message(
            role=role,
            content=content,
            created_at=self._now(),
            file_name=file_name,
            status=status,
            meta=meta or {},
        )
        should_derive_title = (
            role == "user"
            and chat.title == DEFAULT_CHAT_TITLE
            and not any(existing.role == "user" for existing in chat.messages)
        )
        chat.messages.append(message)
        if should_derive_title:
            chat.title = self._derive_chat_title(content, file_name)
        chat.updated_at = self._now()
        return message

    def _derive_chat_title(self, content: str, file_name: Optional[str]) -> str:
        if file_name:
            return file_name[:36]
        compact = " ".join(content.split())
        return compact[:40] if compact else DEFAULT_CHAT_TITLE

    def create_request(
        self,
        user_id: str,
        chat_id: str,
        assistant_message_id: str,
        *,
        meta: Optional[dict] = None,
    ) -> PendingRequest:
        pending = PendingRequest(
            user_id=user_id,
            chat_id=chat_id,
            assistant_message_id=assistant_message_id,
            status="processing",
            created_at=self._now(),
            meta=meta or {},
        )
        self.requests[pending.id] = pending
        return pending

    def get_request(self, request_id: str) -> Optional[PendingRequest]:
        return self.requests.get(request_id)

    def get_active_request(self, user_id: str, chat_id: str) -> Optional[PendingRequest]:
        active = [
            request
            for request in self.requests.values()
            if request.user_id == user_id
            and request.chat_id == chat_id
            and request.status in {"queued", "processing"}
        ]
        if not active:
            return None
        return max(active, key=lambda item: item.created_at)

    def mark_request_forwarded(self, request_id: str, meta: dict) -> PendingRequest:
        request = self.requests[request_id]
        request.meta = {**request.meta, **meta}
        request.status = "processing"
        return request

    def fail_request(self, request_id: str, error_text: str, *, meta: Optional[dict] = None) -> PendingRequest:
        request = self.requests[request_id]
        request.status = "failed"
        request.finished_at = self._now()
        request.meta = {**request.meta, **(meta or {})}

        chat = self.chats[request.chat_id]
        for message in chat.messages:
            if message.id == request.assistant_message_id:
                message.status = "error"
                message.content = error_text
                message.meta = {
                    **request.meta,
                    "error": error_text,
                }
                break
        chat.updated_at = self._now()
        return request

    def apply_response(self, response: ServiceResponse) -> PendingRequest:
        request = self.get_active_request(response.user_id, response.chat_id)
        if request is None:
            raise KeyError(
                f"Active request for user {response.user_id} and chat {response.chat_id} not found"
            )

        if response.received_at is None:
            response.received_at = self._now()

        request.status = "completed" if response.success else "failed"
        request.finished_at = self._now()
        request.response = response

        chat = self.chats[request.chat_id]
        for message in chat.messages:
            if message.id == request.assistant_message_id:
                message.status = "done" if response.success else "error"
                message.content = response.explanation or response.error or "Ответ получен."
                message.meta = {
                    **request.meta,
                    "response_json": response.model_dump(mode="json"),
                    "diagram": response.diagram,
                    "attempt": response.attempt,
                    "source": "service_b",
                }
                break
        chat.updated_at = self._now()
        return request
