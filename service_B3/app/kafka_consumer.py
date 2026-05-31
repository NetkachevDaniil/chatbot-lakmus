from __future__ import annotations

import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import ValidationError

from app.config import settings
from app.models import ResponsePayload

logger = logging.getLogger(__name__)


class KafkaResponseConsumer:
    def __init__(self, processor):
        self.processor = processor
        self._consumer = AIOKafkaConsumer(
            settings.kafka.response_topic,
            bootstrap_servers=settings.kafka.bootstrap_servers,
            group_id=settings.kafka.consumer_group,
            client_id=f"{settings.kafka.client_id}-consumer",
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka.bootstrap_servers,
            client_id=f"{settings.kafka.client_id}-producer",
            value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8"),
        )
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        await self._consumer.start()
        await self._producer.start()
        self._task = asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._consumer.stop()
        await self._producer.stop()

    async def _consume_loop(self) -> None:
        async for record in self._consumer:
            try:
                message = ResponsePayload.model_validate(record.value)
                await self.processor.handle_response(message, self._producer)
                await self._consumer.commit()
            except ValidationError:
                logger.exception("Kafka message has invalid schema: %s", record.value)
                await self._consumer.commit()
            except Exception:
                logger.exception("Failed to process Kafka message: %s", record.value)
