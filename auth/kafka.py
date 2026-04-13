from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from auth.config import Settings

try:
    from aiokafka import AIOKafkaProducer
except ImportError:  # pragma: no cover
    AIOKafkaProducer = None


logger = logging.getLogger(__name__)

#Если я правильно понял что у нас это отдельный микросервис, то он будет в кафку слать данные, слушать ему ничего не надо

class AuthEventProducer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if AIOKafkaProducer is None:
            logger.warning("aiokafka is not installed, Kafka publishing is disabled")
            return

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._producer is None:
            logger.info("Kafka producer is unavailable, skipped event %s", event_type)
            return

        event = {
            "event_type": event_type,
            "service": self.settings.SERVICE_NAME,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        await self._producer.send_and_wait(self.settings.KAFKA_AUTH_TOPIC, event)
