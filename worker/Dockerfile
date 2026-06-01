FROM golang:alpine AS builder

WORKDIR /app

RUN apk add --no-cache git make

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN go build -o /app/bin/worker ./cmd/run

FROM alpine:latest

WORKDIR /app

RUN apk --no-cache add ca-certificates

COPY --from=builder /app/bin/worker /app/worker

COPY --from=builder /app/config_example.yaml /app/config.yaml
CMD ["/app/worker"]
