# 📋 Проект: Chatbot Gateway with Worker Architecture

## 📊 Что было создано

### Полная структура проекта

```
chatbot-lakmus/
│
├── 🌐 GATEWAY (FastAPI API)
│   ├── gateway/
│   │   ├── __init__.py
│   │   ├── app.py              # FastAPI приложение (порт 8001)
│   │   ├── config.py           # Конфигурация Gateway
│   │   └── schemas.py          # Pydantic модели
│   │
│   ├── ⚙️ WORKER (Kafka Consumer)
│   ├── worker/
│   │   ├── __init__.py
│   │   ├── app.py              # Worker приложение
│   │   ├── config.py           # Конфигурация Worker
│   │   ├── file_parser.py      # Парсер файлов (PDF, DOCX, TXT, IMG)
│   │   └── error_handler.py    # Обработчик ошибок
│   │
│   ├── 🔐 AUTH (Аутентификация)
│   ├── auth/
│   │   ├── config.py           # Настройки Auth
│   │   ├── router.py           # Роуты Auth
│   │   └── utils.py            # Утилиты Auth
│   │
│   ├── 🐳 Docker & Config
│   ├── docker-compose.yml      # Kafka + Zookeeper + UI
│   ├── .env.example            # Пример конфигурации
│   │
│   ├── 📝 Документация
│   ├── README.md               # Основной README
│   ├── SETUP.md                # Полная документация
│   ├── QUICKSTART.md           # Быстрый старт (5 минут)
│   ├── PROJECT_STRUCTURE.md    # Этот файл
│   ├── llm_integration_examples.py  # Примеры интеграции с LLM
│   │
│   ├── 🧪 Тестирование
│   ├── test_gateway.py         # Тестовый скрипт
│   │
│   ├── 📁 Runtime
│   ├── uploads/                # Загруженные файлы (создается автоматически)
│   │
│   ├── 📦 Packages
│   ├── main.py                 # Основное приложение
│   └── requiremnts.txt         # Python зависимости
```

---

## 🎯 Основные компоненты

### 1. **API Gateway** (`gateway/app.py`)
**Функции:**
- ✅ REST API для приема запросов
- ✅ Загрузка файлов (PDF, DOCX, TXT, PNG, JPG)
- ✅ Валидация с Pydantic
- ✅ Отправка в Kafka
- ✅ Статус-трекинг запросов
- ✅ Обработка ошибок

**Endpoints:**
| Метод | URL | Описание |
|-------|-----|---------|
| GET | `/health` | Проверка здоровья |
| POST | `/chat` | Отправить текстовый запрос |
| POST | `/upload` | Загрузить файл + запрос |
| GET | `/status/{request_id}` | Получить статус |

**Технологии:**
- FastAPI (асинхронный веб-фреймворк)
- Pydantic (валидация данных)
- aiokafka (асинхронный Kafka клиент)
- aiofiles (асинхронная работа с файлами)

---

### 2. **Worker** (`worker/app.py`)
**Функции:**
- ✅ Слушание Kafka топика (consumer)
- ✅ Парсинг файлов (любого формата)
- ✅ Обработка запросов
- ✅ Отправка результатов в выходной топик
- ✅ Полная обработка ошибок
- ✅ Логирование всех операций

**Обработка файлов:**
- 📄 **TXT** - простое чтение
- 📕 **PDF** - извлечение текста (PyPDF2)
- 📗 **DOCX** - парсинг документов (python-docx)
- 🖼️ **IMG (PNG, JPG)** - OCR с Tesseract

**Обработка ошибок:**
- FileNotFoundError
- FileParsingError
- KafkaError
- ProcessingError

---

### 3. **File Parser** (`worker/file_parser.py`)
**Возможности:**
- ✅ Валидация файлов (размер, формат)
- ✅ Автоматическое определение формата
- ✅ Парсинг разных типов файлов
- ✅ Обработка ошибок кодировки
- ✅ OCR для изображений

**Поддерживаемые форматы:**
```
txt  → Текстовые файлы
pdf  → PDF документы
docx → Word документы
png  → Изображения (PNG)
jpg  → Изображения (JPEG)
jpeg → Изображения (JPEG)
```

---

### 4. **Error Handler** (`worker/error_handler.py`)
**Типы ошибок:**
- FileParsingError
- KafkaError
- ProcessingError

**Функции:**
- ✅ Логирование ошибок
- ✅ Генерация сообщений об ошибках
- ✅ Трейси стека
- ✅ Отправка в Kafka

---

## 🚀 Запуск

### 1. Установка
```bash
pip install -r requiremnts.txt
```

### 2. Запуск Kafka
```bash
docker-compose up -d
```

### 3. Terminal 1 - Gateway
```bash
python -m gateway.app
```

### 4. Terminal 2 - Worker
```bash
python -m worker.app
```

### 5. Terminal 3 - Тестирование
```bash
python test_gateway.py --test all
```

---

## 📊 Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         КЛИЕНТ                                   │
├─────────────────────────────────────────────────────────────────┤
│  POST /chat {"user_id": "...", "user_message": "..."}           │
│  или                                                             │
│  POST /upload {file: ..., user_id: ..., user_message: ...}      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GATEWAY (FastAPI)                            │
├─────────────────────────────────────────────────────────────────┤
│  - Валидирует данные (Pydantic)                                  │
│  - Сохраняет файл (если есть)                                    │
│  - Создает ProcessingTask                                        │
│  - Отправляет в Kafka                                            │
│  - Возвращает request_id                                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
         ┌─────────────────────────────────────┐
         │    KAFKA BROKER (localhost:9092)     │
         ├─────────────────────────────────────┤
         │  TOPIC: chatbot-requests             │
         │  - Очередь задач для обработки      │
         └────────────────┬────────────────────┘
                          │
                          ▼
        ┌──────────────────────────────────────┐
        │        WORKER (Consumer)               │
        ├──────────────────────────────────────┤
        │ 1. Получает сообщение из Kafka       │
        │ 2. Парсит файл (FileParser)          │
        │ 3. Обрабатывает запрос                │
        │ 4. Отправляет результат в Kafka      │
        └────────────────┬─────────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────────┐
        │    KAFKA BROKER (Result Topic)        │
        ├──────────────────────────────────────┤
        │  TOPIC: chatbot-responses             │
        │  - Результаты обработки               │
        └──────────────────────────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────────┐
        │   Клиент получает результат           │
        │   (via GET /status или другой способ) │
        └──────────────────────────────────────┘
```

---

## 📦 Установленные зависимости

### Веб-фреймворк
- **fastapi** - Веб-фреймворк
- **uvicorn** - ASGI сервер
- **starlette** - Асинхронный веб-фреймворк

### Валидация данных
- **pydantic** - Валидация моделей
- **pydantic-settings** - Конфигурация

### Kafka & Асинхронность
- **aiokafka** - Асинхронный Kafka клиент
- **aiofiles** - Асинхронная работа с файлами

### Обработка файлов
- **python-multipart** - Загрузка файлов
- **PyPDF2** - Парсинг PDF
- **python-docx** - Парсинг DOCX
- **Pillow** - Работа с изображениями
- **pytesseract** - OCR

### Аутентификация
- **jwt** - JWT токены
- **passlib** - Хеширование паролей
- **cryptography** - Криптография

### Другое
- **python-dotenv** - Переменные окружения
- **asyncpg** - Асинхронный драйвер PostgreSQL

---

## 🔧 Конфигурация

### Gateway (`gateway/config.py`)
```python
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_INPUT_TOPIC = "chatbot-requests"
KAFKA_OUTPUT_TOPIC = "chatbot-responses"

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_FILE_TYPES = ["pdf", "txt", "docx", "png", "jpg", "jpeg"]
```

### Worker (`worker/config.py`)
```python
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_INPUT_TOPIC = "chatbot-requests"
KAFKA_OUTPUT_TOPIC = "chatbot-responses"
KAFKA_CONSUMER_GROUP = "chatbot-workers"

BATCH_SIZE = 10
PROCESS_TIMEOUT = 300  # 5 minutes
```

---

## 🧪 Тестирование

### Использование test_gateway.py
```bash
# Health check
python test_gateway.py --test health

# Отправить сообщение
python test_gateway.py --test message --user-id user_1 --message "Привет"

# Загрузить файл
python test_gateway.py --test upload --file document.txt --user-id user_1

# Все тесты
python test_gateway.py --test all
```

### Использование cURL
```bash
# Health
curl http://localhost:8001/health

# Чат
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_1", "user_message": "Привет"}'

# Файл
curl -X POST http://localhost:8001/upload \
  -F "file=@document.pdf" \
  -F "user_id=user_1" \
  -F "user_message=Analyze this"
```

---

## 🚀 Масштабирование

### Горизонтальное масштабирование Worker'ов
```bash
# Terminal 2
python -m worker.app

# Terminal 3
python -m worker.app

# Terminal 4
python -m worker.app
```

Kafka автоматически распределит задачи между worker'ами!

### Вертикальное масштабирование Gateway
```bash
# Использовать больше worker потоков
uvicorn gateway.app:app --workers 4
```

---

## 🔌 Интеграция с LLM

Примеры интеграции с различными LLM:
- ✅ OpenAI (GPT-4, GPT-3.5)
- ✅ Anthropic Claude
- ✅ Groq (быстрые инференции)
- ✅ Ollama (локальные модели)

Смотри: `llm_integration_examples.py`

---

## 📚 Документация

| Файл | Описание |
|------|---------|
| [QUICKSTART.md](QUICKSTART.md) | Запуск за 5 минут |
| [SETUP.md](SETUP.md) | Полная документация |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Структура проекта |
| [llm_integration_examples.py](llm_integration_examples.py) | Примеры LLM |

---

## 🎓 Что дальше?

1. **Интеграция с LLM**
   - Добавь OpenAI/Claude/Ollama в worker
   - Реализуй стриминг ответов

2. **База данных**
   - Сохраняй запросы и результаты
   - Реализуй историю диалогов

3. **Аутентификация**
   - Используй JWT токены
   - Добавь роли и разрешения

4. **Monitoring**
   - Добавь метрики (Prometheus)
   - Реализуй трейсинг (Jaeger)
   - Логирование (ELK Stack)

5. **Масштабирование**
   - Docker контейнеры
   - Kubernetes оркестрация
   - Load balancing

---

## 🐛 Troubleshooting

### Kafka не подключается
```bash
docker-compose up -d
docker ps  # Проверь контейнеры
docker logs kafka  # Проверь ошибки
```

### Worker не обрабатывает
```bash
# Проверь консьюмер группу
docker exec kafka kafka-consumer-groups --list --bootstrap-server localhost:9092

# Проверь офсеты
docker exec kafka kafka-consumer-groups --group chatbot-workers \
  --describe --bootstrap-server localhost:9092
```

### Проблемы с файлами
```bash
# Проверь папку uploads
ls -la uploads/

# Проверь логи worker'a
# (они в Terminal с worker'ом)
```

---

## 📞 Support

Для вопросов и проблем:
1. Проверь QUICKSTART.md
2. Прочитай SETUP.md
3. Посмотри примеры в llm_integration_examples.py

---

**Готово! 🎉 Ваш Chatbot Gateway полностью функционален!**
