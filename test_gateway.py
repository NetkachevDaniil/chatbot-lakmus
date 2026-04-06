#!/usr/bin/env python3
"""
Тестовый скрипт для проверки API Gateway
"""

import asyncio
import aiohttp
import json
from pathlib import Path
import argparse


class GatewayTester:
    """Тестер для API Gateway"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
    
    async def health_check(self) -> dict:
        """Проверка здоровья API"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/health") as resp:
                return await resp.json()
    
    async def send_message(self, user_id: str, message: str) -> dict:
        """Отправить чат-сообщение"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "user_id": user_id,
                "user_message": message
            }
            async with session.post(
                f"{self.base_url}/chat",
                json=payload
            ) as resp:
                return await resp.json()
    
    async def upload_file(
        self,
        file_path: str,
        user_id: str,
        message: str,
        description: str = None
    ) -> dict:
        """Загрузить файл"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"error": f"Файл не найден: {file_path}"}
        
        async with aiohttp.ClientSession() as session:
            with open(file_path, 'rb') as f:
                form_data = aiohttp.FormData()
                form_data.add_field('file', f, filename=file_path.name)
                form_data.add_field('user_id', user_id)
                form_data.add_field('user_message', message)
                
                if description:
                    form_data.add_field('description', description)
                
                async with session.post(
                    f"{self.base_url}/upload",
                    data=form_data
                ) as resp:
                    return await resp.json()
    
    async def get_status(self, request_id: str) -> dict:
        """Получить статус запроса"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/status/{request_id}"
            ) as resp:
                return await resp.json()


async def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description="Тестер Chatbot Gateway API")
    parser.add_argument("--url", default="http://localhost:8001", help="URL Gateway")
    parser.add_argument(
        "--test",
        choices=["health", "message", "upload", "all"],
        default="health",
        help="Какой тест запустить"
    )
    parser.add_argument("--file", help="Путь к файлу для загрузки")
    parser.add_argument("--user-id", default="test-user", help="ID пользователя")
    parser.add_argument("--message", default="Тестовое сообщение", help="Сообщение")
    parser.add_argument("--description", help="Описание файла")
    
    args = parser.parse_args()
    
    tester = GatewayTester(args.url)
    
    print(f"🧪 Тестирование Gateway на {args.url}\n")
    
    try:
        if args.test in ["health", "all"]:
            print("1️⃣  Проверка здоровья API...")
            result = await tester.health_check()
            print(f"✓ Ответ: {json.dumps(result, indent=2)}\n")
        
        if args.test in ["message", "all"]:
            print("2️⃣  Отправка текстового сообщения...")
            result = await tester.send_message(args.user_id, args.message)
            print(f"✓ Ответ: {json.dumps(result, indent=2)}\n")
            
            if "request_id" in result:
                print("3️⃣  Проверка статуса запроса...")
                status = await tester.get_status(str(result["request_id"]))
                print(f"✓ Статус: {json.dumps(status, indent=2)}\n")
        
        if args.test in ["upload", "all"]:
            if not args.file:
                print("⚠️  Пропуск теста загрузки (укажите --file)")
            else:
                print(f"4️⃣  Загрузка файла {args.file}...")
                result = await tester.upload_file(
                    args.file,
                    args.user_id,
                    args.message,
                    args.description
                )
                print(f"✓ Ответ: {json.dumps(result, indent=2)}\n")
    
    except aiohttp.ClientConnectorError:
        print(f"❌ Ошибка: Не удалось подключиться к {args.url}")
        print("   Проверьте, запущен ли Gateway?")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())
