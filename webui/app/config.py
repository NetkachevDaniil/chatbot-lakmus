from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_name: str
    access_cookie_name: str
    refresh_cookie_name: str
    access_token_minutes: int
    refresh_token_days: int
    auth_service_base_url: str
    service_a_base_url: str
    service_b_base_url: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("WEBUI_APP_NAME", "Campus AI UI"),
        access_cookie_name=os.getenv("WEBUI_ACCESS_COOKIE", "campus_access_token"),
        refresh_cookie_name=os.getenv("WEBUI_REFRESH_COOKIE", "campus_refresh_token"),
        access_token_minutes=_int_env("WEBUI_ACCESS_TTL_MINUTES", 30),
        refresh_token_days=_int_env("WEBUI_REFRESH_TTL_DAYS", 7),
        auth_service_base_url=os.getenv("WEBUI_AUTH_URL", "http://auth-service.local"),
        service_a_base_url=os.getenv("WEBUI_SERVICE_A_URL", "http://service-a.local"),
        service_b_base_url=os.getenv("WEBUI_SERVICE_B_URL", "http://service-b.local"),
    )
