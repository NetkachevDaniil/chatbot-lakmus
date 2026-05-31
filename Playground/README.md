# Service A

Minimal Python service that:
1) accepts a file and prompt
2) uploads the file to MinIO (TTL 3-4 hours, per-user bucket)
3) publishes a request message to Kafka topic `Request`

Endpoint:
`POST http://localhost:8089/user/{user_id}/chat/{chat_id}/request`

## Local run

Start all services:

```bash
docker-compose up -d
```

## Request example (PowerShell)

```powershell
curl.exe -X POST "http://localhost:8089/user/53f653d5-5ea2-4a1d-8844-e2ad94e01743/chat/adfsadfasdf-dsf-adf-asdf/request" `
  -F "prompt=выведи тех кто ничего не сдал" `
  -F "file=@C:\path\to\grades.xlsx"
```

## Kafka

Service publishes to Kafka via REST Proxy (`kafka-rest` in docker-compose).
