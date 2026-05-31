from __future__ import annotations

from dataclasses import dataclass

from typing import Optional

from ..models import AuthSession
from ..repository import InMemoryRepository


@dataclass(frozen=True)
class ServiceEndpoints:
    auth: str
    service_a: str
    web_ui: str


class MockAuthService:
    def __init__(self, repository: InMemoryRepository, endpoints: ServiceEndpoints) -> None:
        self.repository = repository
        self.endpoints = endpoints

    async def login(self, username: str, password: str) -> Optional[AuthSession]:
        if not username.strip() or not password.strip():
            return None
        user = self.repository.get_or_create_user(username)
        return self.repository.create_session(user)

    async def validate_or_refresh(
        self,
        access_token: Optional[str],
        refresh_token: Optional[str],
    ) -> Optional[AuthSession]:
        active_session = self.repository.get_valid_access_session(access_token)
        if active_session is not None:
            return active_session
        return self.repository.refresh_access_session(refresh_token)

    async def logout(self, access_token: Optional[str], refresh_token: Optional[str]) -> None:
        self.repository.revoke_session(access_token, refresh_token)





