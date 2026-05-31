from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class KafkaConfig(BaseModel):
    bootstrap_servers: str = "kafka:9092"
    response_topic: str = "Response"
    request_topic: str = "Request"
    consumer_group: str = "service-b-consumer"
    client_id: str = "service-b"


class WebUIConfig(BaseModel):
    base_url: str = "http://webui:8090"
    response_path_template: str = "/user/{user_id}/chat/{chat_id}/response"
    timeout_seconds: float = 10.0


class PostgresConfig(BaseModel):
    dsn: str = "postgresql://service_b:service_b@postgres:5432/service_b"


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    app_name: str = "service-b"
    log_level: str = "INFO"
    server: ServerConfig = Field(default_factory=ServerConfig)
    kafka: KafkaConfig = Field(default_factory=KafkaConfig)
    webui: WebUIConfig = Field(default_factory=WebUIConfig)
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_settings() -> AppConfig:
    config_path = Path(os.getenv("APP_CONFIG_PATH", "config.yaml"))
    raw: dict[str, Any] = {}
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    env_override = {
        "server": {
            "host": os.getenv("SERVICE_HOST", raw.get("server", {}).get("host", "0.0.0.0")),
            "port": int(os.getenv("SERVICE_PORT", raw.get("server", {}).get("port", 8000))),
        },
        "kafka": {
            "bootstrap_servers": os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS",
                raw.get("kafka", {}).get("bootstrap_servers", "kafka:9092"),
            ),
            "response_topic": os.getenv(
                "KAFKA_RESPONSE_TOPIC",
                raw.get("kafka", {}).get("response_topic", "Response"),
            ),
            "request_topic": os.getenv(
                "KAFKA_REQUEST_TOPIC",
                raw.get("kafka", {}).get("request_topic", "Request"),
            ),
            "consumer_group": os.getenv(
                "KAFKA_CONSUMER_GROUP",
                raw.get("kafka", {}).get("consumer_group", "service-b-consumer"),
            ),
            "client_id": os.getenv(
                "KAFKA_CLIENT_ID",
                raw.get("kafka", {}).get("client_id", "service-b"),
            ),
        },
        "webui": {
            "base_url": os.getenv(
                "WEBUI_BASE_URL",
                raw.get("webui", {}).get("base_url", "http://webui:8090"),
            ),
            "response_path_template": os.getenv(
                "WEBUI_RESPONSE_PATH_TEMPLATE",
                raw.get("webui", {}).get(
                    "response_path_template",
                    "/user/{user_id}/chat/{chat_id}/response",
                ),
            ),
            "timeout_seconds": float(
                os.getenv(
                    "WEBUI_TIMEOUT_SECONDS",
                    raw.get("webui", {}).get("timeout_seconds", 10.0),
                )
            ),
        },
        "postgres": {
            "dsn": os.getenv(
                "POSTGRES_DSN",
                raw.get("postgres", {}).get(
                    "dsn",
                    "postgresql://service_b:service_b@postgres:5432/service_b",
                ),
            )
        },
        "app_name": os.getenv("APP_NAME", raw.get("app_name", "service-b")),
        "log_level": os.getenv("LOG_LEVEL", raw.get("log_level", "INFO")),
    }
    return AppConfig.model_validate(_deep_merge(raw, env_override))


settings = load_settings()
