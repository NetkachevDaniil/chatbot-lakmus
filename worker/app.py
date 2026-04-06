import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import sys

from worker.config import settings
from worker.file_parser import FileParser
from worker.error_handler import setup_error_handler, ProcessingError

# Логирование
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация обработчика ошибок
error_handler = setup_error_handler(logger)


class ChatbotWorker:
    """Worker для обработки запросов из Kafka"""
    
    def __init__(self):
        self.consumer: AIOKafkaConsumer = None
        self.producer: AIOKafkaProducer = None
        self.is_running = False
    
    async def start(self):
        """Запуск worker'a"""
        try:
            logger.info("🚀 Запуск Chatbot Worker...")
            
            # Инициализация Consumer
            self.consumer = AIOKafkaConsumer(
                settings.KAFKA_INPUT_TOPIC,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=settings.KAFKA_CONSUMER_GROUP,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True
            )
            
            # Инициализация Producer
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            await self.consumer.start()
            await self.producer.start()
            
            logger.info("✓ Consumer и Producer запущены")
            self.is_running = True
            
            # Основной цикл обработки
            await self._process_messages()
        
        except Exception as e:
            logger.error(f"✗ Ошибка при запуске worker'a: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Остановка worker'a"""
        self.is_running = False
        
        if self.consumer:
            await self.consumer.stop()
            logger.info("✓ Consumer остановлен")
        
        if self.producer:
            await self.producer.stop()
            logger.info("✓ Producer остановлен")
        
        logger.info("🛑 Chatbot Worker остановлен")
    
    async def _process_messages(self):
        """Основной цикл обработки сообщений"""
        logger.info(f"📩 Ожидание сообщений из топика '{settings.KAFKA_INPUT_TOPIC}'...")
        
        try:
            async for message in self.consumer:
                if not self.is_running:
                    break
                
                try:
                    await self._process_task(message.value)
                except Exception as e:
                    logger.error(f"Ошибка при обработке сообщения: {e}")
                    # Продолжаем обработку других сообщений
                    continue
        
        except asyncio.CancelledError:
            logger.info("Обработка сообщений отменена")
        except Exception as e:
            logger.error(f"Критическая ошибка в цикле обработки: {e}")
            await self.stop()
            raise
    
    async def _process_task(self, task: dict):
        """
        Обработка одной задачи
        
        Args:
            task: Словарь с данными задачи
        """
        request_id = task.get('request_id', 'unknown')
        
        try:
            logger.info(f"📋 Начало обработки задачи {request_id}")
            
            user_id = task.get('user_id')
            file_path = task.get('file_path', '')
            file_name = task.get('file_name', '')
            user_message = task.get('user_message', '')
            
            # Инициализация результата
            result = {
                'request_id': request_id,
                'user_id': user_id,
                'status': 'completed',
                'parsed_text': '',
                'original_message': user_message,
                'file_name': file_name,
                'processed_at': None
            }
            
            # Обработка файла, если он передан
            if file_path and file_name:
                try:
                    logger.info(f"📄 Парсинг файла: {file_name}")
                    
                    # Валидация файла
                    FileParser.validate_file(file_path, settings.MAX_FILE_SIZE)
                    
                    # Парсинг файла
                    parsed_text = FileParser.parse_file(file_path)
                    result['parsed_text'] = parsed_text
                    
                    logger.info(f"✓ Файл успешно распарсен ({len(parsed_text)} символов)")
                
                except FileNotFoundError as e:
                    logger.warning(f"⚠️ {str(e)}")
                    result['parsed_text'] = f"[Ошибка: {str(e)}]"
                
                except ValueError as e:
                    error_info = error_handler.handle_file_parsing_error(
                        request_id, file_name, e
                    )
                    result['status'] = 'error'
                    result['error'] = error_info['error']
                    logger.error(f"❌ {error_info['error']}")
                
                except ProcessingError as e:
                    error_info = error_handler.handle_file_parsing_error(
                        request_id, file_name, e
                    )
                    result['status'] = 'error'
                    result['error'] = error_info['error']
                
                except Exception as e:
                    error_info = error_handler.handle_processing_error(request_id, e)
                    result['status'] = 'error'
                    result['error'] = error_info['error']
            
            # Отправка результата в output топик
            await self.producer.send_and_wait(
                settings.KAFKA_OUTPUT_TOPIC,
                value=result
            )
            
            error_handler.log_task_completion(
                request_id, 
                result['status'],
                f"Отправлено в {settings.KAFKA_OUTPUT_TOPIC}"
            )
        
        except Exception as e:
            logger.error(f"💥 Критическая ошибка при обработке задачи {request_id}: {e}")
            
            # Отправка сообщения об ошибке
            try:
                error_result = {
                    'request_id': request_id,
                    'user_id': task.get('user_id', 'unknown'),
                    'status': 'error',
                    'error': f"Критическая ошибка при обработке: {str(e)}"
                }
                await self.producer.send_and_wait(
                    settings.KAFKA_OUTPUT_TOPIC,
                    value=error_result
                )
            except Exception as kafka_error:
                logger.error(f"Не удалось отправить сообщение об ошибке в Kafka: {kafka_error}")


async def main():
    """Главная функция"""
    worker = ChatbotWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
        await worker.stop()
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
