"""
Пример интеграции с LLM (OpenAI, Claude, Local LLM)
Это демонстрационный файл - используйте как шаблон
"""

import os
from typing import Optional, AsyncGenerator
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Пример 1: Интеграция с OpenAI API
# ============================================================================

class OpenAIProcessor:
    """Обработчик с использованием OpenAI API"""
    
    def __init__(self, api_key: Optional[str] = None):
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
            self.available = True
        except ImportError:
            logger.warning("OpenAI не установлен. Установите: pip install openai")
            self.available = False
    
    async def process(
        self,
        user_message: str,
        parsed_text: str = "",
        system_prompt: str = None
    ) -> str:
        """
        Обработать запрос с помощью ChatGPT
        
        Args:
            user_message: Оригинальное сообщение пользователя
            parsed_text: Распарсенный текст из файла
            system_prompt: Пользовательский системный промпт
            
        Returns:
            Ответ от модели
        """
        if not self.available:
            return "[OpenAI API недоступен]"
        
        try:
            # Подготовка контекста
            context = ""
            if parsed_text:
                context = f"\n\nДокумент:\n{parsed_text[:5000]}"  # Лимит для экономии токенов
            
            system_prompt = system_prompt or (
                "Ты - полезный помощник, анализирующий документы. "
                "Отвечай на русском языке."
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{user_message}{context}"}
            ]
            
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo",  # или "gpt-3.5-turbo" для экономии
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Ошибка OpenAI: {e}")
            return f"[Ошибка при обработке: {str(e)}]"


# ============================================================================
# Пример 2: Интеграция с Anthropic Claude
# ============================================================================

class ClaudeProcessor:
    """Обработчик с использованием Claude API"""
    
    def __init__(self, api_key: Optional[str] = None):
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(
                api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
            )
            self.available = True
        except ImportError:
            logger.warning("Anthropic не установлен. Установите: pip install anthropic")
            self.available = False
    
    async def process(
        self,
        user_message: str,
        parsed_text: str = "",
        system_prompt: str = None
    ) -> str:
        """
        Обработать запрос с помощью Claude
        
        Args:
            user_message: Оригинальное сообщение пользователя
            parsed_text: Распарсенный текст из файла
            system_prompt: Пользовательский системный промпт
            
        Returns:
            Ответ от модели
        """
        if not self.available:
            return "[Claude API недоступен]"
        
        try:
            # Подготовка контекста
            context = ""
            if parsed_text:
                context = f"\n\nДокумент:\n{parsed_text[:8000]}"  # Claude имеет больший контекст
            
            system_prompt = system_prompt or (
                "Ты - полезный помощник, анализирующий документы. "
                "Отвечай на русском языке."
            )
            
            message = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"{user_message}{context}"}
                ]
            )
            
            return message.content[0].text
        
        except Exception as e:
            logger.error(f"Ошибка Claude: {e}")
            return f"[Ошибка при обработке: {str(e)}]"


# ============================================================================
# Пример 3: Интеграция с локальной моделью (Ollama)
# ============================================================================

class OllamaProcessor:
    """Обработчик с использованием локальной модели Ollama"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        try:
            import httpx
            self.client = httpx.AsyncClient(base_url=base_url)
            self.model = model
            self.available = True
        except ImportError:
            logger.warning("httpx не установлен. Установите: pip install httpx")
            self.available = False
    
    async def process(
        self,
        user_message: str,
        parsed_text: str = "",
        system_prompt: str = None
    ) -> str:
        """
        Обработать запрос с помощью Ollama
        
        Args:
            user_message: Оригинальное сообщение пользователя
            parsed_text: Распарсенный текст из файла
            system_prompt: Пользовательский системный промпт
            
        Returns:
            Ответ от модели
        """
        if not self.available:
            return "[Ollama недоступен]"
        
        try:
            # Подготовка контекста
            context = ""
            if parsed_text:
                context = f"\n\nДокумент:\n{parsed_text[:4000]}"
            
            system_prompt = system_prompt or (
                "Ты - полезный помощник, анализирующий документы."
            )
            
            prompt = f"{system_prompt}\n\n{user_message}{context}"
            
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            result = response.json()
            return result.get("response", "[Пустой ответ от Ollama]")
        
        except Exception as e:
            logger.error(f"Ошибка Ollama: {e}")
            return f"[Ошибка при обработке: {str(e)}]"


# ============================================================================
# Пример 4: Интеграция с Groq (быстрые инференции)
# ============================================================================

class GroqProcessor:
    """Обработчик с использованием Groq API"""
    
    def __init__(self, api_key: Optional[str] = None):
        try:
            from groq import AsyncGroq
            self.client = AsyncGroq(api_key=api_key or os.getenv("GROQ_API_KEY"))
            self.available = True
        except ImportError:
            logger.warning("Groq не установлен. Установите: pip install groq")
            self.available = False
    
    async def process(
        self,
        user_message: str,
        parsed_text: str = "",
        system_prompt: str = None
    ) -> str:
        """
        Обработать запрос с помощью Groq
        
        Args:
            user_message: Оригинальное сообщение пользователя
            parsed_text: Распарсенный текст из файла
            system_prompt: Пользовательский системный промпт
            
        Returns:
            Ответ от модели
        """
        if not self.available:
            return "[Groq API недоступен]"
        
        try:
            # Подготовка контекста
            context = ""
            if parsed_text:
                context = f"\n\nДокумент:\n{parsed_text[:5000]}"
            
            system_prompt = system_prompt or (
                "Ты - полезный помощник, анализирующий документы. "
                "Отвечай на русском языке."
            )
            
            message = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{user_message}{context}"}
                ],
                model="mixtral-8x7b-32768",  # Быстрая модель
                temperature=0.7,
                max_tokens=1024
            )
            
            return message.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Ошибка Groq: {e}")
            return f"[Ошибка при обработке: {str(e)}]"


# ============================================================================
# Пример 5: Реализация в Worker
# ============================================================================

"""
Добавьте это в worker/app.py в методе _process_task:

async def _process_task(self, task: dict):
    # ... существующий код ...
    
    # Инициализация LLM обработчика
    llm_processor = OpenAIProcessor()  # или ClaudeProcessor(), OllamaProcessor()
    
    if result['status'] == 'completed':
        # Обработка с LLM
        try:
            logger.info(f"🤖 Отправка в LLM...")
            llm_response = await llm_processor.process(
                user_message=user_message,
                parsed_text=result.get('parsed_text', ''),
                system_prompt="Анализируй документ и ответь на вопрос пользователя"
            )
            result['llm_response'] = llm_response
            result['processed'] = True
            logger.info(f"✓ LLM обработано")
        except Exception as e:
            logger.error(f"❌ Ошибка LLM: {e}")
            result['llm_error'] = str(e)
"""


# ============================================================================
# Пример 6: Стриминг ответов
# ============================================================================

class StreamingProcessor:
    """Пример обработки со стрйингом ответов"""
    
    def __init__(self):
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI()
            self.available = True
        except ImportError:
            self.available = False
    
    async def process_stream(
        self,
        user_message: str,
        parsed_text: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        Обработать запрос со стрймингом
        
        Yields:
            Куски ответа по мере их поступления
        """
        if not self.available:
            yield "[OpenAI API недоступен]"
            return
        
        try:
            context = f"\n\nДокумент:\n{parsed_text[:5000]}" if parsed_text else ""
            
            stream = await self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "Ты - полезный помощник"},
                    {"role": "user", "content": f"{user_message}{context}"}
                ],
                stream=True,
                max_tokens=2000
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except Exception as e:
            yield f"[Ошибка: {str(e)}]"


# ============================================================================
# Пример 7: Кэширование ответов
# ============================================================================

from functools import lru_cache
import hashlib


class CachedProcessor:
    """Процессор с кэшированием ответов"""
    
    def __init__(self):
        self.processor = OpenAIProcessor()
        self.cache = {}
    
    def _get_cache_key(self, user_message: str, parsed_text: str) -> str:
        """Получить ключ для кэша"""
        content = f"{user_message}:{parsed_text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def process(
        self,
        user_message: str,
        parsed_text: str = "",
        use_cache: bool = True
    ) -> str:
        """
        Обработать с кэшированием
        
        Args:
            user_message: Сообщение пользователя
            parsed_text: Текст документа
            use_cache: Использовать кэш
            
        Returns:
            Ответ (из кэша или новый)
        """
        cache_key = self._get_cache_key(user_message, parsed_text)
        
        if use_cache and cache_key in self.cache:
            logger.info(f"📦 Ответ из кэша")
            return self.cache[cache_key]
        
        response = await self.processor.process(user_message, parsed_text)
        
        if use_cache:
            self.cache[cache_key] = response
        
        return response


# ============================================================================
# Установка зависимостей
# ============================================================================

"""
Для использования различных LLM добавьте в requirements.txt:

# OpenAI
openai>=1.0.0

# Anthropic Claude
anthropic>=0.7.0

# Groq
groq>=0.4.0

# Ollama
httpx>=0.24.0

# Для стриминга и асинхронности
aiohttp>=3.9.0
"""
