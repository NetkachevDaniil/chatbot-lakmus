# LITMUS-OR-LAKMUS

## Auth service

FastAPI-based микросервис аутентификации:

- JWT access, refresh tokens
- PostgreSQL - используется драйвер asyncpg
- Kafka для связи микросервисов

### Endpoints

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /health`

### Environment

В .env должно быть:

- `SECRET_KEY`
- `DATABASE_URL`
- `KAFKA_BOOTSTRAP_SERVERS`
- `KAFKA_AUTH_TOPIC`

в .env.example пример
### Kafka events

Сервис отправляет ивенты в кафку в топик "auth.events" по умолчанию:

- `user_registered`
- `user_logged_in`
- `token_refreshed`
- `user_logged_out`
