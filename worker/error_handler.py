import logging


class ProcessingError(Exception):
    """Базовое исключение для ошибок обработки"""
    pass


class FileParsingError(ProcessingError):
    """Ошибка при парсинге файла"""
    pass


class KafkaError(ProcessingError):
    """Ошибка при работе с Kafka"""
    pass


def setup_error_handler(logger: logging.Logger):
    """Настройка обработчика ошибок"""
    return ErrorHandler(logger)


class ErrorHandler:
    """Обработчик ошибок для worker'a"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def handle_file_parsing_error(self, request_id: str, file_name: str, error: Exception):
        """Обработка ошибки парсинга файла"""
        error_msg = f"Ошибка при парсинге файла '{file_name}': {str(error)}"
        self.logger.error(f"[{request_id}] {error_msg}")
        return {
            "error": error_msg,
            "error_type": "FILE_PARSING_ERROR"
        }
    
    def handle_kafka_error(self, request_id: str, error: Exception):
        """Обработка ошибки Kafka"""
        error_msg = f"Ошибка при работе с Kafka: {str(error)}"
        self.logger.error(f"[{request_id}] {error_msg}")
        return {
            "error": error_msg,
            "error_type": "KAFKA_ERROR"
        }
    
    def handle_processing_error(self, request_id: str, error: Exception):
        """Обработка общей ошибки обработки"""
        error_msg = f"Ошибка при обработке запроса: {str(error)}"
        self.logger.error(f"[{request_id}] {error_msg}")
        return {
            "error": error_msg,
            "error_type": "PROCESSING_ERROR"
        }
    
    def log_task_completion(self, request_id: str, status: str, details: str = ""):
        """Логирование завершения задачи"""
        self.logger.info(f"[{request_id}] Статус: {status}. {details}")
