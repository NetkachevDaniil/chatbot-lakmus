import json

import requests

from .config import Settings


def send_json(settings: Settings, topic: str, payload: dict) -> None:
    url = settings.kafka_rest_url.rstrip("/") + f"/topics/{topic}"
    body = {"records": [{"value": payload}]}
    headers = {
        "Content-Type": "application/vnd.kafka.json.v2+json",
        "Accept": "application/vnd.kafka.v2+json",
    }
    response = requests.post(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), headers=headers, timeout=10)
    response.raise_for_status()


__all__ = ["send_json"]
