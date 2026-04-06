from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """Gateway configuration"""
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_INPUT_TOPIC: str = "chatbot-requests"
    KAFKA_OUTPUT_TOPIC: str = "chatbot-responses"
    
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: list = ["pdf", "txt", "docx", "png", "jpg", "jpeg"]
    
    API_TITLE: str = "Chatbot Gateway API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API Gateway для обработки запросов через LLM"

    model_config = SettingsConfigDict(env_file='.env')


settings = GatewaySettings()
