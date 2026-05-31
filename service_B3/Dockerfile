FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.yaml ./config.yaml
COPY app ./app

EXPOSE 8000

CMD ["python", "-m", "app.main"]
