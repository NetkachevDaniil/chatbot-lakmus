from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Worker configuration"""
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_INPUT_TOPIC: str = "chatbot-requests"
    KAFKA_OUTPUT_TOPIC: str = "chatbot-responses"
    KAFKA_CONSUMER_GROUP: str = "chatbot-workers"
    
    # Processing settings
    BATCH_SIZE: int = 10
    PROCESS_TIMEOUT: int = 300  # 5 minutes
    
    # File parsing
    SUPPORTED_FORMATS: list = ["pdf", "txt", "docx", "png", "jpg", "jpeg"]
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file='.env')


settings = WorkerSettings()
