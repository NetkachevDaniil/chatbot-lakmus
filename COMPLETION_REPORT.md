# ✅ Chatbot Gateway with Worker - Project Complete

## 📋 Что было реализовано

### ✅ **API Gateway** (FastAPI)
Находится в папке: `gateway/`

**Функциональность:**
- 🌐 REST API для приема запросов и файлов
- 📤 Загрузка файлов (PDF, DOCX, TXT, PNG, JPG, JPEG)
- 🔄 Асинхронная отправка данных в Kafka
- ✅ Валидация данных через Pydantic
- 📊 Статус-трекинг запросов
- 🛡️ Обработка ошибок и исключений

**Endpoints:**
```
GET  /health              - Проверка здоровья API
POST /chat               - Отправить текстовый запрос
POST /upload             - Загрузить файл + запрос
GET  /status/{id}        - Получить статус запроса
```

**Запуск:**
```bash
python -m gateway.app
```
API доступна на `http://localhost:8001`

---

### ✅ **Worker** (Kafka Consumer)
Находится в папке: `worker/`

**Функциональность:**
- 📩 Слушание Kafka топика `chatbot-requests`
- 📄 Парсинг файлов (PDF, DOCX, TXT, IMG с OCR)
- ⚙️ Обработка задач с полной обработкой ошибок
- 📤 Отправка результатов в топик `chatbot-responses`
- 📋 Логирование всех операций
- 🔄 Готов к масштабированию (horizontally scalable)

**Поддерживаемые форматы:**
- 📄 TXT (простое чтение)
- 📕 PDF (PyPDF2)
- 📗 DOCX (python-docx)
- 🖼️ PNG, JPG, JPEG (OCR с Tesseract)

**Запуск:**
```bash
python -m worker.app
```

---

### ✅ **File Parser Module**
Файл: `worker/file_parser.py`

**Возможности:**
- ✅ Валидация файлов (размер, формат)
- ✅ Автоматическое определение типа файла
- ✅ Парсинг разных форматов
- ✅ Обработка ошибок кодировки
- ✅ OCR для изображений

---

### ✅ **Error Handler**
Файл: `worker/error_handler.py`

**Обработка:**
- FileParsingError
- KafkaError
- ProcessingError
- General exceptions

---

### ✅ **Docker Setup**
Файл: `docker-compose.yml`

**Содержит:**
- Apache Kafka
- Apache Zookeeper
- Kafka UI (веб-интерфейс)

**Запуск:**
```bash
docker-compose up -d
```

---

### ✅ **Документация**
Созданы файлы:

| Файл | Описание |
|------|---------|
| **QUICKSTART.md** | ⚡ Запуск за 5 минут |
| **SETUP.md** | 📚 Полная документация |
| **PROJECT_STRUCTURE.md** | 📋 Структура проекта |
| **llm_integration_examples.py** | 🤖 Примеры LLM интеграции |
| **.env.example** | ⚙️ Пример конфигурации |

---

### ✅ **Тестирование**
Файл: `test_gateway.py`

**Использование:**
```bash
# Проверка здоровья
python test_gateway.py --test health

# Отправить сообщение
python test_gateway.py --test message --message "Привет"

# Загрузить файл
python test_gateway.py --test upload --file document.pdf

# Все тесты
python test_gateway.py --test all
```

---

## 🚀 Быстрый старт

### Шаг 1: Установка зависимостей
```bash
pip install -r requiremnts.txt
```

### Шаг 2: Запуск Kafka
```bash
docker-compose up -d
```

### Шаг 3: Запуск Gateway (Terminal 1)
```bash
python -m gateway.app
```

### Шаг 4: Запуск Worker (Terminal 2)
```bash
python -m worker.app
```

### Шаг 5: Тестирование (Terminal 3)
```bash
python test_gateway.py --test health
```

---

## 📊 Архитектура

```
Клиент
  ↓
API Gateway (FastAPI) [порт 8001]
  ↓
Kafka Broker [localhost:9092]
  ├─→ chatbot-requests topic
  ├─→ chatbot-responses topic
  ↓
Worker (Consumer + Processor)
  ├─→ File Parser
  ├─→ Error Handler
  ├─→ LLM Integration (готово к добавлению)
  ↓
Результаты в Kafka
```

---

## 📦 Структура папок

```
chatbot-lakmus/
├── gateway/                    # API Gateway
│   ├── __init__.py
│   ├── app.py                 # FastAPI приложение (8001)
│   ├── config.py              # Конфиг Gateway
│   └── schemas.py             # Pydantic модели
│
├── worker/                     # Worker for processing
│   ├── __init__.py
│   ├── app.py                 # Worker приложение
│   ├── config.py              # Конфиг Worker
│   ├── file_parser.py         # Парсер файлов
│   └── error_handler.py       # Обработчик ошибок
│
├── auth/                       # Аутентификация (existing)
│   ├── config.py
│   ├── router.py
│   └── utils.py
│
├── uploads/                    # Загруженные файлы (auto-created)
│
├── main.py                     # Main app
├── requiremnts.txt            # Python dependencies
├── docker-compose.yml         # Kafka setup
├── .env.example               # Config template
├── test_gateway.py            # Testing script
│
├── 📚 QUICKSTART.md           # 5-min start guide
├── 📚 SETUP.md                # Full documentation
├── 📚 PROJECT_STRUCTURE.md    # This overview
├── 📚 llm_integration_examples.py  # LLM examples
│
└── README.md, .gitignore, etc.
```

---

## 🔌 Интеграция с LLM (готово!)

Смотри файл: `llm_integration_examples.py`

Поддерживаемые LLM:
- ✅ OpenAI (GPT-4, GPT-3.5-turbo)
- ✅ Anthropic Claude
- ✅ Groq (быстрые инференции)
- ✅ Ollama (локальные модели)

Примеры включают:
- Базовую интеграцию
- Стриминг ответов
- Кэширование результатов

---

## 📋 Примеры использования

### cURL - отправить сообщение
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_1",
    "user_message": "Анализируй этот документ"
  }'
```

### cURL - загрузить файл
```bash
curl -X POST http://localhost:8001/upload \
  -F "file=@document.pdf" \
  -F "user_id=user_1" \
  -F "user_message=Please analyze"
```

### Python
```python
import requests

# Отправить сообщение
response = requests.post(
    "http://localhost:8001/chat",
    json={
        "user_id": "user_1",
        "user_message": "Hello"
    }
)
print(response.json())
```

---

## 🎯 Ключевые особенности

✅ **Асинхронность** - FastAPI + asyncio  
✅ **Масштабируемость** - Горизонтальное масштабирование worker'ов через Kafka  
✅ **Обработка ошибок** - Полная обработка с логированием  
✅ **Валидация** - Pydantic schemas  
✅ **Парсинг файлов** - Поддержка PDF, DOCX, TXT, IMG  
✅ **Kafka интеграция** - Асинхронный producer/consumer  
✅ **LLM готовность** - Примеры для OpenAI, Claude, Groq, Ollama  
✅ **Документация** - Полная и подробная  
✅ **Тестирование** - Готовый test_gateway.py  

---

## 🚀 Что дальше?

### 1. Интеграция с LLM (важно!)
```python
# В worker/app.py добавить обработку с LLM:
from llm_integration_examples import OpenAIProcessor

llm = OpenAIProcessor()
response = await llm.process(user_message, parsed_text)
```

### 2. База данных
- PostgreSQL для хранения запросов/результатов
- Redis для кэша

### 3. Мониторинг
- Prometheus метрики
- Jaeger трейсинг
- ELK логирование

### 4. Масштабирование
- Docker контейнеры
- Kubernetes

### 5. Аутентификация
- JWT токены (уже есть модуль auth/)
- OAuth2 интеграция

---

## 🐛 Troubleshooting

**Kafka не подключается?**
```bash
docker-compose up -d
docker ps  # проверь контейнеры
docker logs kafka  # проверь логи
```

**Worker не обрабатывает сообщения?**
- Проверь, что Gateway отправляет в правильный топик
- Проверь логи Worker
- Убедись, что Kafka запущен

**Проблемы с парсингом файлов?**
- Для PDF: `pip install PyPDF2`
- Для DOCX: `pip install python-docx`
- Для OCR: установи Tesseract

---

## 📚 Документация

Полная документация доступна в файлах:

1. **QUICKSTART.md** - Запуск за 5 минут
2. **SETUP.md** - Полная документация с примерами
3. **PROJECT_STRUCTURE.md** - Структура проекта
4. **llm_integration_examples.py** - Примеры LLM

---

## ✨ Готово к использованию!

Проект полностью готов к:
- ✅ Разработке
- ✅ Тестированию
- ✅ Развертыванию
- ✅ Масштабированию

**Наслаивайте свои функции на этом крепком фундаменте!** 🚀

---

**Вопросы? Смотри SETUP.md или QUICKSTART.md!**
