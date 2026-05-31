from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import asyncpg
import httpx
from fastapi import FastAPI
import uvicorn

from app.config import settings
from app.database import MetricsRepository
from app.kafka_consumer import KafkaResponseConsumer
from app.processor import ResponseProcessor
from app.webui_client import WebUIClient

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))


@asynccontextmanager
async def lifespan(app: FastAPI):
    pg_pool = await asyncpg.create_pool(settings.postgres.dsn, min_size=1, max_size=5)
    metrics_repository = MetricsRepository(pg_pool)
    await metrics_repository.initialize()
    webui_client = WebUIClient(
        httpx.AsyncClient(timeout=settings.webui.timeout_seconds)
    )
    processor = ResponseProcessor(metrics_repository, webui_client)
    consumer = KafkaResponseConsumer(processor)

    app.state.pg_pool = pg_pool
    app.state.metrics_repository = metrics_repository
    app.state.webui_client = webui_client
    app.state.processor = processor
    app.state.consumer = consumer

    await consumer.start()
    yield

    await consumer.stop()
    await webui_client.aclose()
    await pg_pool.close()


app = FastAPI(title="Service B", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
async def health_db() -> dict[str, str]:
    await app.state.pg_pool.fetchval("SELECT 1;")
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
    )
