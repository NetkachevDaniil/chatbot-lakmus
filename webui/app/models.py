from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class User(BaseModel):
    id: str
    username: str
    display_name: str


class AuthSession(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: datetime
    user: User
    refreshed: bool = False


class Message(BaseModel):
    id: str = Field(default_factory=lambda: new_id("msg"))
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    file_name: Optional[str] = None
    status: Literal["done", "pending", "error"] = "done"
    meta: dict[str, Any] = Field(default_factory=dict)


class Chat(BaseModel):
    id: str = Field(default_factory=lambda: new_id("chat"))
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[Message] = Field(default_factory=list)


class PendingRequest(BaseModel):
    id: str = Field(default_factory=lambda: new_id("req"))
    user_id: str
    chat_id: str
    assistant_message_id: str
    status: Literal["queued", "processing", "completed", "failed"] = "queued"
    created_at: datetime
    finished_at: Optional[datetime] = None
    result: Optional[dict[str, Any]] = None

