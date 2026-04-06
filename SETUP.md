# Chatbot Gateway Setup Guide

Полная архитектура чат-бота с API Gateway и Worker для обработки запросов через Kafka.

## Архитектура

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌──────────────────────────┐
│   API Gateway (port 8001)│  ◄── Принимает запросы и файлы
│   - FastAPI              │
│   - Pydantic schemas     │
│   - Kafka Producer       │
└──────────────┬───────────┘
               │
               ▼
        ┌─────────────┐
        │   Kafka     │  ◄── Message Broker
        │ (localhost) │
        └──────┬──────┘
               │
               ▼
┌──────────────────────────┐
│  Worker Process          │  ◄── Обрабатывает запросы
│  - File Parser           │
│  - Kafka Consumer        │
│  - Error Handling        │
│  - Output to Kafka       │
└──────────────────────────┘
```

## Установка зависимостей

### Windows/Linux/Mac

```bash
# Установка Python пакетов
pip install -r requiremnts.txt
```

### Зависимости для OCR (опционально для парсинга изображений)

Для работы с изображениями требуется Tesseract:

**На Windows:**
1. Скачать и установить Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
2. Указать путь в коде (если нужно):
```python
import pytesseract
pytesseract.pytesseract.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

**На Linux:**
```bash
sudo apt-get install tesseract-ocr
```

**На macOS:**
```bash
brew install tesseract
```

## Запуск Kafka

### Используя Docker (рекомендуется)

```bash
# docker-compose.yml
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
  
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
```

Запуск:
```bash
docker-compose up -d
```

### Вручную (если Kafka уже установлен)

Убедитесь, что Kafka доступна на `localhost:9092`

## Конфигурация

### `.env` файл (в корне проекта)

```env
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_INPUT_TOPIC=chatbot-requests
KAFKA_OUTPUT_TOPIC=chatbot-responses
KAFKA_CONSUMER_GROUP=chatbot-workers

# Gateway
MAX_FILE_SIZE=52428800
ALLOWED_FILE_TYPES=["pdf", "txt", "docx", "png", "jpg", "jpeg"]

# Worker
BATCH_SIZE=10
PROCESS_TIMEOUT=300
LOG_LEVEL=INFO
```

## Запуск сервисов

### Terminal 1: API Gateway

```bash
cd chatbot-lakmus
python -m gateway.app
```

API будет доступен на `http://localhost:8001`

### Terminal 2: Worker

```bash
cd chatbot-lakmus
python -m worker.app
```

Worker начнет слушать Kafka топик `chatbot-requests`

## API Endpoints

### 1. Health Check

```bash
GET /health
```

**Ответ:**
```json
{
  "status": "healthy",
  "service": "chatbot-gateway"
}
```

### 2. Отправить текстовый запрос

```bash
POST /chat
Content-Type: application/json

{
  "user_id": "user_123",
  "user_message": "Проанализируй документ",
  "metadata": {"source": "web"}
}
```

**Ответ:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_123",
  "status": "pending",
  "message": "Ваш запрос принят и отправлен на обработку"
}
```

### 3. Загрузить файл

```bash
POST /upload
Content-Type: multipart/form-data

Fields:
- file: <file.pdf>
- user_id: user_123
- user_message: Проанализируй этот отчет
- description: Квартальный отчет (optional)
```

**Ответ:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_123",
  "status": "pending",
  "message": "Файл 'report.pdf' загружен и отправлен на обработку"
}
```

### 4. Получить статус запроса

```bash
GET /status/550e8400-e29b-41d4-a716-446655440000
```

**Ответ:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_123",
  "status": "processing",
  "message": "Запрос находится в обработке"
}
```

## Примеры использования

### cURL

```bash
# Отправить чат-сообщение
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_1", "user_message": "Hello world"}'

# Загрузить файл
curl -X POST http://localhost:8001/upload \
  -F "file=@document.pdf" \
  -F "user_id=user_1" \
  -F "user_message=Analyze this"
```

### Python

```python
import requests

# Отправить сообщение
response = requests.post(
    "http://localhost:8001/chat",
    json={
        "user_id": "user_1",
        "user_message": "Привет, анализируй файл"
    }
)
print(response.json())

# Загрузить файл
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8001/upload",
        data={
            "user_id": "user_1",
            "user_message": "Analyze this PDF"
        },
        files={"file": f}
    )
print(response.json())
```

## Структура папок

```
chatbot-lakmus/
├── gateway/                 # API Gateway
│   ├── __init__.py
│   ├── app.py              # FastAPI приложение
│   ├── config.py           # Конфиг Gateway
│   └── schemas.py          # Pydantic модели
│
├── worker/                  # Worker для обработки
│   ├── __init__.py
│   ├── app.py              # Worker приложение
│   ├── config.py           # Конфиг Worker
│   ├── file_parser.py      # Парсер файлов
│   └── error_handler.py    # Обработчик ошибок
│
├── auth/                    # Auth модуль
│   ├── config.py
│   ├── router.py
│   └── utils.py
│
├── uploads/                 # Загруженные файлы (создается автоматически)
│
├── main.py                  # Основное приложение
├── requiremnts.txt          # Python зависимости
├── .env                     # Конфигурация (создать)
├── .gitignore
└── README.md
```

## Обработка ошибок

### Worker обрабатывает следующие ошибки:

1. **FILE_NOT_FOUND** - Файл не найден
2. **FILE_PARSING_ERROR** - Ошибка при парсинге файла
3. **INVALID_FILE_FORMAT** - Неподдерживаемый формат файла
4. **FILE_SIZE_EXCEEDED** - Размер файла превышает лимит
5. **KAFKA_ERROR** - Ошибка при работе с Kafka
6. **PROCESSING_ERROR** - Ошибка при обработке запроса

Все ошибки логируются и отправляются в output топик с статусом `error`.

## Мониторинг

### Просмотр логов Gateway
```bash
# Terminal с Gateway показывает все запросы и операции
```

### Просмотр логов Worker
```bash
# Terminal с Worker показывает обработку файлов и ошибки
```

### Проверка Kafka

```bash
# Просмотр топиков
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Просмотр сообщений в топике
docker exec kafka kafka-console-consumer --topic chatbot-requests \
  --from-beginning --bootstrap-server localhost:9092
```

## Производительность и масштабирование

- **Gateway**: Может обрабатывать множество запросов одновременно (асинхронный)
- **Worker**: Масштабируется горизонтально - запустите несколько worker'ов с одной группой консьюмера
- **Kafka**: Обеспечивает очередь сообщений с гарантией доставки

## Дополнительные возможности

### Добавление поддержки новых форматов файлов

В `worker/file_parser.py` добавьте метод:

```python
@staticmethod
def _parse_xlsb(file_path: str) -> str:
    """Парсинг XLSB файла"""
    try:
        import openpyxl
        # Логика парсинга
    except ImportError:
        return "[Требуется openpyxl]"
```

### Интеграция с LLM

Добавьте в `worker/app.py` обработку с LLM (например, OpenAI API):

```python
from openai import AsyncOpenAI

async def send_to_llm(parsed_text: str, user_message: str):
    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Ты помощник."},
            {"role": "user", "content": f"{user_message}\n\n{parsed_text}"}
        ]
    )
    return response.choices[0].message.content
```

## Решение проблем

### Kafka не подключается
- Проверьте, запущен ли Kafka: `docker ps`
- Проверьте адрес: должен быть `localhost:9092`
- Проверьте логи Kafka: `docker logs kafka`

### Worker не обрабатывает сообщения
- Проверьте, что Gateway отправляет сообщения в правильный топик
- Проверьте логи Worker
- Убедитесь, что Kafka консьюмер может подключиться

### Проблемы с парсингом файлов
- Для PDF: установите `pip install PyPDF2`
- Для DOCX: установите `pip install python-docx`
- Для OCR: установите Tesseract (см. раздел выше)

## Лицензия

MIT
