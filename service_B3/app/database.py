from __future__ import annotations

import json

import asyncpg

from app.models import ResponsePayload


class MetricsRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def initialize(self) -> None:
        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS response_metrics (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    success BOOLEAN NOT NULL,
                    error TEXT NOT NULL,
                    start_time TIMESTAMPTZ NULL,
                    end_time TIMESTAMPTZ NULL,
                    duration_ms BIGINT NULL,
                    llm_calls INTEGER NULL,
                    analyzer_used TEXT NULL,
                    sheet_used TEXT NULL,
                    payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            await connection.execute(
                """
                ALTER TABLE response_metrics
                ADD COLUMN IF NOT EXISTS chat_id TEXT;
                """
            )

    async def save_metrics(self, response: ResponsePayload) -> None:
        metrics = response.metrics
        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO response_metrics (
                    user_id,
                    chat_id,
                    attempt,
                    success,
                    error,
                    start_time,
                    end_time,
                    duration_ms,
                    llm_calls,
                    analyzer_used,
                    sheet_used,
                    payload
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb
                );
                """,
                response.user_id,
                response.chat_id,
                response.attempt,
                response.success,
                response.error,
                metrics.start_time if metrics else None,
                metrics.end_time if metrics else None,
                metrics.duration_ms if metrics else None,
                metrics.llm_calls if metrics else None,
                metrics.analyzer_used if metrics else None,
                metrics.sheet_used if metrics else None,
                json.dumps(response.model_dump(mode="json"), ensure_ascii=False),
            )
