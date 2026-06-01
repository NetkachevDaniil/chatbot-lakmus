from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.config import get_settings
from app.db import create_pool, init_db
from app.kafka import AuthEventProducer
from app.router import router as auth_router
from app.service import AuthService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    pool = await create_pool(settings)
    await init_db(pool)

    producer = AuthEventProducer(settings)
    await producer.start()

    app.state.db_pool = pool
    app.state.auth_producer = producer
    app.state.auth_service = AuthService(pool=pool, producer=producer)

    try:
        yield
    finally:
        await producer.stop()
        await pool.close()


app = FastAPI(title="Auth Service", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)


@app.get("/health")
async def healthcheck():
    return {"status": "ok", "service": "auth-service"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
