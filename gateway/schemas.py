from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
import uuid


class ChatRequest(BaseModel):
    """Схема для запроса обработки"""
    request_id: UUID = Field(default_factory=uuid.uuid4)
    user_id: str
    user_message: str = Field(..., min_length=1, max_length=10000)
    metadata: Optional[dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "user_message": "Проанализируй этот документ",
                "metadata": {"source": "web"}
            }
        }


class ChatResponse(BaseModel):
    """Схема для ответа от API"""
    request_id: UUID
    user_id: str
    status: str = Field(..., pattern="^(pending|processing|completed|error)$")
    message: Optional[str] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user_123",
                "status": "pending",
                "message": "Ваш запрос принят и отправлен на обработку"
            }
        }


class FileUploadRequest(BaseModel):
    """Схема для загрузки файла"""
    user_id: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "description": "Отчет за квартал"
            }
        }


class ProcessingTask(BaseModel):
    """Внутренняя схема для обработки задачи"""
    request_id: UUID
    user_id: str
    file_path: str
    file_name: str
    user_message: str
    metadata: Optional[dict] = None
