# 🚀 Quick Start Guide

## За 5 минут к работающему Chatbot Gateway

### Шаг 1: Запуск Kafka (Docker)

```bash
# Убедитесь, что Docker установлен
docker-compose up -d

# Проверка (должны быть контейнеры kafka, zookeeper, kafka-ui)
docker ps
```

### Шаг 2: Установка зависимостей

```bash
pip install -r requiremnts.txt
```

### Шаг 3: Запуск Gateway (Terminal 1)

```bash
python -m gateway.app
```

Должно вывести:
```
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

### Шаг 4: Запуск Worker (Terminal 2)

```bash
python -m worker.app
```

Должно вывести:
```
2024-01-15 10:30:00 - worker.app - INFO - 🚀 Запуск Chatbot Worker...
2024-01-15 10:30:01 - worker.app - INFO - ✓ Consumer и Producer запущены
2024-01-15 10:30:01 - worker.app - INFO - 📩 Ожидание сообщений из топика 'chatbot-requests'...
```

## Тестирование

### Способ 1: Используя test_gateway.py

```bash
# Terminal 3: Проверка здоровья
python test_gateway.py --test health

# Отправка сообщения
python test_gateway.py --test message --user-id user_1 --message "Привет"

# Загрузка файла
python test_gateway.py --test upload --file document.txt --user-id user_1
```

### Способ 2: Используя cURL

```bash
# Health Check
curl http://localhost:8001/health

# Отправить сообщение
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_1", "user_message": "Привет мир"}'

# Загрузить файл
curl -X POST http://localhost:8001/upload \
  -F "file=@test.txt" \
  -F "user_id=user_1" \
  -F "user_message=Analyze this"
```

### Способ 3: Используя Python requests

```python
import requests

# Отправить сообщение
response = requests.post(
    "http://localhost:8001/chat",
    json={
        "user_id": "user_123",
        "user_message": "Привет, как дела?"
    }
)
print(response.json())

# Загрузить файл
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8001/upload",
        data={
            "user_id": "user_123",
            "user_message": "Please analyze this"
        },
        files={"file": f}
    )
print(response.json())
```

## Просмотр Kafka сообщений

### Используя Kafka UI (веб интерфейс)
```
http://localhost:8080
```

### Используя консоль

```bash
# Просмотр топиков
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Просмотр сообщений в input топике
docker exec kafka kafka-console-consumer --topic chatbot-requests \
  --from-beginning --bootstrap-server localhost:9092

# Просмотр сообщений в output топике
docker exec kafka kafka-console-consumer --topic chatbot-responses \
  --from-beginning --bootstrap-server localhost:9092
```

## Проверка логов

```bash
# Gateway логи (видны в Terminal 1)
# Worker логи (видны в Terminal 2)

# Docker логи
docker logs kafka
docker logs zookeeper
```

## Структура проекта

```
chatbot-lakmus/
├── gateway/           # 🌐 API Gateway (FastAPI)
├── worker/            # ⚙️  Worker (Kafka Consumer)
├── auth/              # 🔐 Аутентификация
├── uploads/           # 📁 Загруженные файлы
├── test_gateway.py    # 🧪 Тестовый скрипт
├── docker-compose.yml # 🐳 Kafka & Zookeeper
├── .env.example       # ⚙️  Конфигурация
└── SETUP.md          # 📚 Полная документация
```

## Основные endpoints

| Метод | Endpoint | Описание |
|-------|----------|---------|
| GET | `/health` | Проверка здоровья |
| POST | `/chat` | Отправить сообщение |
| POST | `/upload` | Загрузить файл |
| GET | `/status/{request_id}` | Получить статус |

## Типичный flow

```
1. Клиент отправляет запрос/файл на Gateway (POST /chat или /upload)
   ↓
2. Gateway отправляет задачу в Kafka топик 'chatbot-requests'
   ↓
3. Worker слушает топик 'chatbot-requests' и получает задачу
   ↓
4. Worker парсит файл (если есть) и обрабатывает запрос
   ↓
5. Worker отправляет результат в топик 'chatbot-responses'
   ↓
6. (Опционально) Клиент может получить результат из 'chatbot-responses'
```

## Решение проблем

### Ошибка: "Connection refused" при подключении к Kafka

```bash
# Проверьте, запущены ли контейнеры
docker ps

# Если не запущены, запустите
docker-compose up -d

# Проверьте логи Kafka
docker logs kafka
```

### Worker не обрабатывает сообщения

```bash
# Проверьте, что топик создан
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Проверьте логи Worker
# (должны быть в Terminal 2)
```

### Проблемы с файлами

- Убедитесь, что папка `uploads/` существует (создается автоматически)
- Проверьте права доступа
- Максимальный размер файла: 50MB (можно изменить в .env)

## Что дальше?

### 1. Интеграция с LLM
Отредактируйте `worker/app.py` и добавьте обработку с OpenAI/Claude/Local LLM

### 2. Добавить базу данных
Сохраняйте запросы и результаты в PostgreSQL/MongoDB

### 3. Добавить аутентификацию
Используйте модуль `auth/` для защиты endpoints

### 4. Масштабирование
Запустите несколько worker'ов для параллельной обработки:
```bash
python -m worker.app  # Worker 1
python -m worker.app  # Worker 2
python -m worker.app  # Worker 3
```

Kafka автоматически распределит задачи между ними!

## Полезные ссылки

- [FastAPI документация](https://fastapi.tiangolo.com/)
- [Kafka документация](https://kafka.apache.org/documentation/)
- [aiokafka library](https://aiokafka.readthedocs.io/)
- [Pydantic документация](https://docs.pydantic.dev/)

---

**Готово! 🎉 Ваш Chatbot Gateway работает!**

Для полной документации см.: [SETUP.md](SETUP.md)
