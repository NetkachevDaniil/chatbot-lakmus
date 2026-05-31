from pydantic import BaseModel


class RequestMessage(BaseModel):
    user_id: str
    chat_id: str
    file_format: str
    file_url: str
    prompt: str
    attempt: int


__all__ = ["RequestMessage"]
