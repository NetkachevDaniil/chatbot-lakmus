import logging
import uuid

from dotenv import load_dotenv
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from .config import Settings
from .kafka_rest import send_json
from .minio_client import S3Error, build_minio_client, ensure_bucket, upload_and_get_link
from .schemas import RequestMessage
from .utils import detect_file_format, sanitize_bucket_name

load_dotenv()

app = FastAPI(title="Service A")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("service_a")


@app.post("/user/{user_id}/chat/{chat_id}/request")
def create_request(
    user_id: str,
    chat_id: str,
    prompt: str = Form(...),
    file: UploadFile = File(...),
):
    return _handle_request(user_id=user_id, chat_id=chat_id, prompt=prompt, file=file)


@app.post("/request")
def create_request_default(
    prompt: str = Form(...),
    file: UploadFile = File(...),
):
    default_user_id = "demo-user"
    default_chat_id = "demo-chat"
    return _handle_request(
        user_id=default_user_id, chat_id=default_chat_id, prompt=prompt, file=file
    )


def _handle_request(user_id: str, chat_id: str, prompt: str, file: UploadFile):
    settings = Settings()

    bucket = sanitize_bucket_name(user_id)
    object_name = f"{uuid.uuid4()}_{file.filename}"

    client = build_minio_client(settings)
    try:
        ensure_bucket(client, bucket)
        file_url = upload_and_get_link(
            client=client,
            bucket=bucket,
            object_name=object_name,
            data=file.file,
            content_type=file.content_type,
            ttl_hours=settings.file_ttl_hours,
        )
    except S3Error as exc:
        logger.exception("MinIO error during upload")
        raise HTTPException(status_code=500, detail=f"MinIO error: {exc}") from exc

    message = RequestMessage(
        user_id=user_id,
        chat_id=chat_id,
        file_format=detect_file_format(file.filename or ""),
        file_url=file_url,
        prompt=prompt,
        attempt=0,
    )

    try:
        send_json(settings, settings.kafka_topic_request, message.model_dump())
    except Exception as exc:
        logger.exception("Kafka error during publish")
        raise HTTPException(status_code=500, detail=f"Kafka error: {exc}") from exc

    return message.model_dump()


@app.post("/demo")
def demo_request(prompt: str = Form(...)):
    now = datetime.now(timezone.utc).isoformat()
    return {"status": "received", "prompt": prompt, "attempt": 0, "received_at": now}


@app.get("/health")
def health():
    return {"status": "ok"}
