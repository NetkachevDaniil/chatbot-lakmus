from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RequestPayload(BaseModel):
    user_id: str = Field(min_length=1)
    chat_id: str = Field(min_length=1)
    file_format: str = Field(min_length=1)
    file_url: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    attempt: int = Field(ge=0)


class MetricsPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    llm_calls: int | None = Field(default=None, ge=0)
    analyzer_used: str | None = None
    sheet_used: str | None = None


class ResponsePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request: RequestPayload
    metrics: MetricsPayload | None = None
    user_id: str = Field(min_length=1)
    chat_id: str = Field(min_length=1)
    success: bool
    explanation: str = ""
    diagram: str = ""
    attempt: int = Field(ge=0)
    error: str = ""

    @model_validator(mode="after")
    def normalize_and_validate(self) -> "ResponsePayload":
        if self.request.attempt != self.attempt:
            raise ValueError("request.attempt must match attempt")
        if self.request.chat_id != self.chat_id:
            raise ValueError("request.chat_id must match chat_id")
        if self.error.strip():
            self.success = False
        return self

    def sanitized_for_webui(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json", exclude={"request", "metrics"})
        return payload

    def retry_request(self) -> dict[str, Any]:
        retry_payload = self.request.model_copy(update={"attempt": self.request.attempt + 1})
        return retry_payload.model_dump(mode="json")
