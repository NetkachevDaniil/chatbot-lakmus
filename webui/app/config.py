from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DOTENV_PATH = ROOT_DIR / ".env"


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


_load_dotenv(DOTENV_PATH)


@dataclass(frozen=True)
class Settings:
    app_name: str
    access_cookie_name: str
    refresh_cookie_name: str
    access_token_minutes: int
    refresh_token_days: int
    auth_service_base_url: str
    service_a_base_url: str
    web_ui_base_url: str
    vk_group_id: int
    vk_access_token: str
    vk_api_version: str
    vk_long_poll_wait: int
    vk_forward_url: str
    vk_payload_log_path: str
    vk_max_text_file_bytes: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("WEBUI_APP_NAME", "Lakmus"),
        access_cookie_name=os.getenv("WEBUI_ACCESS_COOKIE", "campus_access_token"),
        refresh_cookie_name=os.getenv("WEBUI_REFRESH_COOKIE", "campus_refresh_token"),
        access_token_minutes=_int_env("WEBUI_ACCESS_TTL_MINUTES", 30),
        refresh_token_days=_int_env("WEBUI_REFRESH_TTL_DAYS", 7),
        auth_service_base_url=os.getenv("WEBUI_AUTH_URL", "http://auth-service.local"),
        service_a_base_url=os.getenv("WEBUI_SERVICE_A_URL", "http://localhost:8089"),
        web_ui_base_url=os.getenv("WEBUI_BASE_URL", "http://localhost:8090"),
        vk_group_id=_int_env("WEBUI_VK_GROUP_ID", 0),
        vk_access_token=os.getenv("WEBUI_VK_ACCESS_TOKEN", ""),
        vk_api_version=os.getenv("WEBUI_VK_API_VERSION", "5.199"),
        vk_long_poll_wait=_int_env("WEBUI_VK_LONG_POLL_WAIT", 25),
        vk_forward_url=os.getenv("WEBUI_VK_FORWARD_URL", ""),
        vk_payload_log_path=os.getenv("WEBUI_VK_PAYLOAD_LOG_PATH", "data/vk_inbox.jsonl"),
        vk_max_text_file_bytes=_int_env("WEBUI_VK_MAX_TEXT_FILE_BYTES", 200000),
    )
