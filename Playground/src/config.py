import os


def _get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return value


class Settings:
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool
    file_ttl_hours: int
    kafka_rest_url: str
    kafka_topic_request: str

    def __init__(self) -> None:
        self.minio_endpoint = _get_env("MINIO_ENDPOINT")
        self.minio_access_key = _get_env("MINIO_ACCESS_KEY")
        self.minio_secret_key = _get_env("MINIO_SECRET_KEY")
        self.minio_secure = _get_env("MINIO_SECURE", "false").lower() == "true"
        self.file_ttl_hours = int(_get_env("FILE_TTL_HOURS", "4"))
        self.kafka_rest_url = _get_env("KAFKA_REST_URL")
        self.kafka_topic_request = _get_env("KAFKA_TOPIC_REQUEST", "Request")
