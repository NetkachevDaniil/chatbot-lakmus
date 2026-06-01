from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from ..models import AuthSession, User
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


class HttpAuthService:
    def __init__(self, endpoints: ServiceEndpoints, access_minutes: int) -> None:
        self.base_url = endpoints.auth.rstrip("/")
        self.access_minutes = access_minutes

    def _expires_at(self) -> datetime:
        return datetime.now(tz=timezone.utc) + timedelta(minutes=self.access_minutes)

    def _session_from_payload(self, payload: dict, *, refreshed: bool = False) -> AuthSession:
        user_payload = payload["user"]
        tokens = payload["tokens"]
        return AuthSession(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_at=self._expires_at(),
            user=User(
                id=str(user_payload["id"]),
                username=user_payload["email"],
                display_name=user_payload.get("full_name") or user_payload["email"],
            ),
            refreshed=refreshed,
        )

    def _session_from_user(
        self,
        user_payload: dict,
        access_token: str,
        refresh_token: str,
    ) -> AuthSession:
        return AuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=self._expires_at(),
            user=User(
                id=str(user_payload["id"]),
                username=user_payload["email"],
                display_name=user_payload.get("full_name") or user_payload["email"],
            ),
        )

    async def login(self, email: str, password: str) -> Optional[AuthSession]:
        if not email.strip() or not password.strip():
            return None

        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            try:
                response = await client.post(
                    "/auth/login",
                    json={"email": email.strip(), "password": password},
                )
            except httpx.HTTPError:
                return None

        if response.status_code != 200:
            return None
        return self._session_from_payload(response.json())

    async def validate_or_refresh(
        self,
        access_token: Optional[str],
        refresh_token: Optional[str],
    ) -> Optional[AuthSession]:
        if access_token:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
                try:
                    response = await client.get(
                        "/auth/me",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                except httpx.HTTPError:
                    response = None
            if response is not None and response.status_code == 200 and refresh_token:
                return self._session_from_user(response.json(), access_token, refresh_token)

        if not refresh_token:
            return None

        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            try:
                response = await client.post(
                    "/auth/refresh",
                    json={"refresh_token": refresh_token},
                )
            except httpx.HTTPError:
                return None

        if response.status_code != 200:
            return None
        return self._session_from_payload(response.json(), refreshed=True)

    async def logout(self, access_token: Optional[str], refresh_token: Optional[str]) -> None:
        if not refresh_token:
            return

        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            try:
                await client.post("/auth/logout", json={"refresh_token": refresh_token})
            except httpx.HTTPError:
                return





