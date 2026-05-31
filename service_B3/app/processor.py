from __future__ import annotations

import logging

from aiokafka import AIOKafkaProducer

from app.config import settings
from app.database import MetricsRepository
from app.models import ResponsePayload
from app.webui_client import WebUIClient

logger = logging.getLogger(__name__)


class ResponseProcessor:
    def __init__(self, metrics_repository: MetricsRepository, webui_client: WebUIClient):
        self.metrics_repository = metrics_repository
        self.webui_client = webui_client

    async def handle_response(
        self,
        response: ResponsePayload,
        producer: AIOKafkaProducer,
    ) -> None:
        await self.metrics_repository.save_metrics(response)

        if response.error.strip() and response.attempt == 0:
            retry_payload = response.retry_request()
            await producer.send_and_wait(settings.kafka.request_topic, retry_payload)
            logger.info(
                "Retry request sent to topic %s for user_id=%s attempt=%s",
                settings.kafka.request_topic,
                response.user_id,
                retry_payload["attempt"],
            )
            return

        await self.webui_client.send_response(
            response.user_id,
            response.chat_id,
            response.sanitized_for_webui(),
        )
        logger.info("Response forwarded to webUI for user_id=%s", response.user_id)
