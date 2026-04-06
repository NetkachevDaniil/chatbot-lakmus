import json
import logging
import aiofiles
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
import os
from pathlib import Path
from aiokafka import AIOKafkaProducer
import uuid

from gateway.config import settings
from gateway.schemas import ChatRequest, ChatResponse, FileUploadRequest, ProcessingTask

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание FastAPI приложения
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION
)

# Глобальная переменная для продюсера Kafka
kafka_producer: Optional[AIOKafkaProducer] = None

# Директория для загруженных файлов
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.on_event("startup")
async def startup_event():
    """Инициализация Kafka продюсера при запуске приложения"""
    global kafka_producer
    try:
        kafka_producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await kafka_producer.start()
        logger.info("✓ Kafka продюсер запущен")
    except Exception as e:
        logger.error(f"✗ Ошибка при подключении к Kafka: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Закрытие Kafka продюсера при остановке приложения"""
    global kafka_producer
    if kafka_producer:
        await kafka_producer.stop()
        logger.info("✓ Kafka продюсер остановлен")


@app.get("/health", tags=["Health"])
async def health_check():
    """Проверка здоровья API"""
    return {
        "status": "healthy",
        "service": "chatbot-gateway"
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def send_message(request: ChatRequest):
    """
    Отправить текстовый запрос для обработки
    
    - **user_id**: ID пользователя
    - **user_message**: Текст сообщения
    - **metadata**: Дополнительные метаданные
    """
    try:
        # Создание задачи для обработки
        task = ProcessingTask(
            request_id=request.request_id,
            user_id=request.user_id,
            file_path="",
            file_name="",
            user_message=request.user_message,
            metadata=request.metadata or {}
        )
        
        # Отправка в Kafka
        await kafka_producer.send_and_wait(
            settings.KAFKA_INPUT_TOPIC,
            value=task.model_dump()
        )
        
        logger.info(f"Запрос {request.request_id} отправлен в Kafka")
        
        return ChatResponse(
            request_id=request.request_id,
            user_id=request.user_id,
            status="pending",
            message="Ваш запрос принят и отправлен на обработку"
        )
    
    except Exception as e:
        logger.error(f"Ошибка при обработке чат-запроса: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обработке запроса"
        )


@app.post("/upload", response_model=ChatResponse, tags=["File Upload"])
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    user_message: str = Form(...),
    description: Optional[str] = Form(None)
):
    """
    Загрузить файл и обработать
    
    - **file**: Файл для загрузки
    - **user_id**: ID пользователя
    - **user_message**: Вопрос/описание запроса
    - **description**: Дополнительное описание файла
    """
    try:
        # Валидация расширения файла
        if file.filename is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Имя файла не может быть пустым"
            )
        
        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in settings.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Тип файла .{file_ext} не поддерживается. "
                       f"Разрешенные типы: {', '.join(settings.ALLOWED_FILE_TYPES)}"
            )
        
        # Проверка размера файла
        file_content = await file.read()
        if len(file_content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Размер файла превышает максимум ({settings.MAX_FILE_SIZE} байт)"
            )
        
        # Сохранение файла
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = UPLOAD_DIR / unique_filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        request_id = uuid.uuid4()
        
        # Создание задачи для обработки
        task = ProcessingTask(
            request_id=request_id,
            user_id=user_id,
            file_path=str(file_path),
            file_name=file.filename,
            user_message=user_message,
            metadata={
                "description": description,
                "original_filename": file.filename
            }
        )
        
        # Отправка в Kafka
        await kafka_producer.send_and_wait(
            settings.KAFKA_INPUT_TOPIC,
            value=task.model_dump()
        )
        
        logger.info(f"Файл {unique_filename} загружен и запрос {request_id} отправлен в Kafka")
        
        return ChatResponse(
            request_id=request_id,
            user_id=user_id,
            status="pending",
            message=f"Файл '{file.filename}' загружен и отправлен на обработку"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при загрузке файла"
        )


@app.get("/status/{request_id}", response_model=ChatResponse, tags=["Status"])
async def get_status(request_id: str):
    """
    Получить статус обработки запроса
    
    - **request_id**: ID запроса для проверки
    """
    # Здесь можно добавить логику проверки статуса из БД или кэша
    return ChatResponse(
        request_id=request_id,
        user_id="unknown",
        status="processing",
        message="Запрос находится в обработке"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
