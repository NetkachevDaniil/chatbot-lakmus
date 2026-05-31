# Service B

`Service B` принимает сообщения из Kafka-топика `Response`, валидирует их, сохраняет `metrics` в Postgres и затем решает, что делать дальше:

- если в ответе есть ошибка и это первая попытка (`attempt = 0`), сервис отправляет `request` обратно в Kafka-топик `Request`, увеличив `attempt` на `1`;
- если ответ успешный или ошибка пришла уже не на первой попытке, сервис отправляет результат в webUI по HTTP.

В webUI уходит не весь исходный ответ, а его очищенная версия: поля `request` и `metrics` удаляются.

## Что лежит в проекте

- [app/main.py](C:/Users/Admin/Documents/PD_bot/app/main.py) поднимает `FastAPI` приложение, создает зависимости на старте и корректно закрывает их при остановке
- [app/config.py](C:/Users/Admin/Documents/PD_bot/app/config.py) читает `config.yaml` и накладывает сверху переменные окружения
- [app/models.py](C:/Users/Admin/Documents/PD_bot/app/models.py) описывает входной `response`, вложенный `request`, `metrics` и правила валидации
- [app/kafka_consumer.py](C:/Users/Admin/Documents/PD_bot/app/kafka_consumer.py) создает Kafka consumer и producer, читает `Response` и передает сообщение в обработчик
- [app/processor.py](C:/Users/Admin/Documents/PD_bot/app/processor.py) содержит основную бизнес-логику: сохранить метрики, решить retry или отправку в webUI
- [app/database.py](C:/Users/Admin/Documents/PD_bot/app/database.py) создает таблицу `response_metrics` и сохраняет туда данные
- [app/webui_client.py](C:/Users/Admin/Documents/PD_bot/app/webui_client.py) отправляет итоговый JSON в webUI
- [config.yaml](C:/Users/Admin/Documents/PD_bot/config.yaml) содержит основной конфиг сервиса
- [docker-compose.yml](C:/Users/Admin/Documents/PD_bot/docker-compose.yml) поднимает Kafka, Postgres и сам сервис

## Полный жизненный цикл сообщения

### 1. Старт приложения

Когда запускается сервис, код из [app/main.py](C:/Users/Admin/Documents/PD_bot/app/main.py) делает следующее:

1. создает пул подключений к Postgres через `asyncpg.create_pool(...)`
2. создает `MetricsRepository`
3. вызывает `initialize()`, чтобы создать таблицу `response_metrics`, если ее еще нет
4. создает HTTP-клиент `httpx.AsyncClient`
5. создает `ResponseProcessor`
6. создает `KafkaResponseConsumer`
7. запускает Kafka consumer и Kafka producer

Пока все эти зависимости не поднялись, приложение не считается стартовавшим.

При завершении сервиса:

1. останавливается Kafka consumer
2. закрывается HTTP-клиент
3. закрывается пул Postgres

## Как читается конфиг

Конфиг устроен так:

1. сервис читает файл [config.yaml](C:/Users/Admin/Documents/PD_bot/config.yaml)
2. затем поверх значений из YAML накладывает переменные окружения
3. итоговый объект конфигурации кладется в `settings`

Это реализовано в [app/config.py](C:/Users/Admin/Documents/PD_bot/app/config.py).

Главные секции конфига:

- `server`: хост и порт HTTP-сервиса
- `kafka`: адрес брокера, имена топиков, consumer group, client id
- `webui`: базовый URL webUI, шаблон пути и timeout
- `postgres`: DSN для подключения к БД

Если нужно переопределить конфиг без изменения YAML, можно использовать переменные окружения из [.env.example](C:/Users/Admin/Documents/PD_bot/.env.example).

## Какой JSON приходит из Kafka

Сервис ожидает сообщение вида:

```json
{
  "request": {
    "user_id": "53f653d5-5ea2-4a1d-8844-e2ad94e01743",
    "chat_id": "adfsadfasdf-dsf-adf-asdf",
    "file_format": "excel",
    "file_url": "http://host/file.excel",
    "prompt": "выведи тех кто ничего не сдал",
    "attempt": 0
  },
  "metrics": {
    "start_time": "2026-04-12T01:08:32.6598842+03:00",
    "end_time": "2026-04-12T01:08:41.3739781+03:00",
    "duration_ms": 8713,
    "llm_calls": 2,
    "analyzer_used": "filter",
    "sheet_used": "241-3211"
  },
  "user_id": "89619a36-7261-49f6-aaa6-1911c9d12983",
  "chat_id": "adfsadfasdf-dsf-adf-asdf",
  "success": true,
  "explanation": "Голик получил средний балл 3,67 и занял второе место.",
  "diagram": "graph TD\n A[Голик]\n --> B[Средний балл 3,67]\n",
  "attempt": 0,
  "error": ""
}
```

Эта схема описана в [app/models.py](C:/Users/Admin/Documents/PD_bot/app/models.py).

## Как работает валидация

Валидация выполняется через `Pydantic` в [app/models.py](C:/Users/Admin/Documents/PD_bot/app/models.py).

### Что проверяется

- `request.user_id`, `request.chat_id`, `request.file_format`, `request.file_url`, `request.prompt` должны быть непустыми строками
- `request.attempt` должен быть `>= 0`
- верхнеуровневые `user_id` и `chat_id` должны быть непустыми
- верхнеуровневый `attempt` должен быть `>= 0`
- `request.attempt` должен совпадать с верхнеуровневым `attempt`
- `request.chat_id` должен совпадать с верхнеуровневым `chat_id`

### Как нормализуется `success`

Если поле `error` не пустое, модель принудительно ставит `success = false`, даже если в исходном JSON пришло `true`.

Это нужно, чтобы дальше бизнес-логика не полагалась на конфликтующие данные.

### Как обрабатываются `metrics`

Поле `metrics` может отсутствовать целиком, а его внутренние поля могут отсутствовать частично.

В этом случае:

- сообщение остается валидным
- сервис все равно сохраняет запись в Postgres
- отсутствующие значения сохраняются как `NULL`

## Как работает Kafka consumer

Класс `KafkaResponseConsumer` из [app/kafka_consumer.py](C:/Users/Admin/Documents/PD_bot/app/kafka_consumer.py):

1. создает `AIOKafkaConsumer`, который слушает топик `Response`
2. создает `AIOKafkaProducer`, который нужен для отправки retry-запросов в топик `Request`
3. на старте запускает и consumer, и producer
4. в фоне крутит бесконечный цикл `_consume_loop()`

### Что происходит внутри `_consume_loop()`

Для каждого Kafka record:

1. `record.value` десериализуется из JSON
2. строится `ResponsePayload`
3. если схема валидна, сообщение передается в `ResponseProcessor.handle_response(...)`
4. после успешной обработки вызывается `consumer.commit()`

Если сообщение не прошло `Pydantic`-валидацию:

- ошибка пишется в лог
- offset коммитится
- такое сообщение больше повторно не обрабатывается

Если в процессе обработки случилась другая ошибка:

- ошибка пишется в лог
- offset не коммитится
- Kafka потом отдаст это сообщение повторно

Это важно: повторная обработка возможна именно для технических сбоев, например если недоступен Postgres или webUI.

## Как работает основная бизнес-логика

Вся основная логика находится в [app/processor.py](C:/Users/Admin/Documents/PD_bot/app/processor.py), в методе `handle_response(...)`.

Порядок действий такой:

1. сохранить `metrics` и весь payload в Postgres
2. проверить, есть ли ошибка и равен ли `attempt` нулю
3. если это первая ошибка, сформировать retry payload и отправить его в Kafka `Request`
4. если это не первая ошибка или ошибки нет, отправить очищенный ответ в webUI

### Почему сначала сохраняются метрики

Даже если дальше webUI недоступен или retry-отправка упадет, попытка обработки уже будет зафиксирована в БД.

Это полезно для аудита и последующей диагностики.

## Как формируется retry в Kafka

Если выполняются оба условия:

- `error` не пустой
- `attempt == 0`

тогда сервис берет поле `request`, увеличивает в нем `attempt` на `1` и отправляет результат в топик `Request`.

Формирование retry payload описано в методе `retry_request()` модели [app/models.py](C:/Users/Admin/Documents/PD_bot/app/models.py).

Пример:

Исходный `request`:

```json
{
  "user_id": "53f653d5-5ea2-4a1d-8844-e2ad94e01743",
  "chat_id": "adfsadfasdf-dsf-adf-asdf",
  "file_format": "excel",
  "file_url": "http://host/file.excel",
  "prompt": "выведи тех кто ничего не сдал",
  "attempt": 0
}
```

Что уйдет в `Request`:

```json
{
  "user_id": "53f653d5-5ea2-4a1d-8844-e2ad94e01743",
  "chat_id": "adfsadfasdf-dsf-adf-asdf",
  "file_format": "excel",
  "file_url": "http://host/file.excel",
  "prompt": "выведи тех кто ничего не сдал",
  "attempt": 1
}
```

Если `attempt` уже равен `1` или больше, повторная отправка в `Request` не делается.

## Как формируется запрос в webUI

Если retry не нужен, сервис отправляет HTTP POST в webUI.

За это отвечает [app/webui_client.py](C:/Users/Admin/Documents/PD_bot/app/webui_client.py).

### URL

По умолчанию URL собирается по шаблону:

```text
http://localhost:8090/user/{user_id}/chat/{chat_id}/response
```

Путь формируется из верхнеуровневых `user_id` и `chat_id`.

### Что именно уходит в webUI

Метод `sanitized_for_webui()` в [app/models.py](C:/Users/Admin/Documents/PD_bot/app/models.py) берет исходный `ResponsePayload` и удаляет:

- `request`
- `metrics`

В результате webUI получает такой JSON:

```json
{
  "user_id": "89619a36-7261-49f6-aaa6-1911c9d12983",
  "chat_id": "adfsadfasdf-dsf-adf-asdf",
  "success": true,
  "explanation": "Голик получил средний балл 3,67 и занял второе место.",
  "diagram": "graph TD\n A[Голик]\n --> B[Средний балл 3,67]\n",
  "attempt": 0,
  "error": ""
}
```

Если webUI возвращает HTTP-ошибку, `httpx` бросит исключение, оно уйдет вверх, offset не закоммитится и сообщение будет обработано заново.

## Как сохраняются метрики в Postgres

Работа с БД находится в [app/database.py](C:/Users/Admin/Documents/PD_bot/app/database.py).

При старте вызывается `initialize()`, который:

1. создает таблицу `response_metrics`, если ее нет
2. отдельно выполняет `ALTER TABLE ... ADD COLUMN IF NOT EXISTS chat_id TEXT`

### Какие поля сохраняются

В таблицу пишутся:

- `user_id`
- `chat_id`
- `attempt`
- `success`
- `error`
- `start_time`
- `end_time`
- `duration_ms`
- `llm_calls`
- `analyzer_used`
- `sheet_used`
- полный исходный payload в `payload jsonb`
- `created_at`

### Зачем сохранять полный payload

Это дает возможность:

- посмотреть исходное Kafka-сообщение без восстановления по логам
- разбирать ошибки задним числом
- анализировать, какие данные реально приходили от upstream-сервиса

## HTTP endpoints самого сервиса

Сам сервис почти не предоставляет бизнес-API. В [app/main.py](C:/Users/Admin/Documents/PD_bot/app/main.py) есть только служебные endpoints:

- `GET /health` возвращает `{"status": "ok"}`
- `GET /health/db` делает `SELECT 1` в Postgres и тоже возвращает `{"status": "ok"}`

То есть этот сервис не предназначен для приема бизнес-запросов по HTTP, он в первую очередь Kafka consumer.

## Запуск

Рекомендуемый способ запуска:

```bash
docker compose up --build
```

После запуска должны быть доступны:

- Kafka: `localhost:19092`
- Postgres: `localhost:5432`
- Service B: `http://localhost:8000`
- Health check: `http://localhost:8000/health`

## Что важно учитывать при сопровождении

- если Postgres не поднимется, сервис вообще не стартует, потому что подключение к БД создается в `lifespan`
- если Kafka недоступна, сервис тоже не завершит startup успешно
- если сообщение невалидно по схеме, оно логируется и пропускается без ретрая
- если сообщение валидное, но упал Postgres, Kafka producer или webUI, offset не коммитится и сообщение придет снова
- при повторной обработке того же сообщения запись в таблицу метрик будет вставлена еще раз, потому что сейчас в БД нет дедупликации

## Коротко в одном сценарии

Ниже типичный успешный сценарий:

1. в Kafka `Response` приходит JSON
2. consumer читает его
3. `Pydantic` валидирует и нормализует поля
4. сервис сохраняет метрики и весь payload в Postgres
5. сервис удаляет `request` и `metrics`
6. сервис отправляет остаток JSON в webUI по URL с `user_id` и `chat_id`
7. после успешного завершения offset коммитится

Сценарий первой ошибки:

1. в `Response` приходит JSON с непустым `error`
2. модель ставит `success = false`
3. сервис сохраняет данные в Postgres
4. сервис берет `request`, увеличивает `attempt`
5. отправляет обновленный `request` в Kafka `Request`
6. offset коммитится
