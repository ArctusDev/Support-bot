import asyncio
import logging
from aiogram import  types
from aiogram.dispatcher.middlewares.base import BaseMiddleware

logger = logging.getLogger(__name__)

class WriteLimit(BaseMiddleware):
    def __init__(self, limit: float = 2.0):
        super().__init__()
        self.limit = limit
        self.users = {}

    async def __call__(self, handler, event: types.Message, data):
        user_id = event.from_user.id
        current_time = asyncio.get_event_loop().time()
        print("Пункт 1")
        # Проблема с кнопкой /start
        if event.text and (event.text.startswith ("/start") or event.text.startswith ("/help")):
            print(f"Пропускаем команду {event.text}")
            return await handler(event, data)
        # Если пользователь уже отправлял команду недавно
        if user_id in self.users and (current_time - self.users[user_id]) < self.limit:
            logger.warning(f"Пользователь {user_id} превышает лимит команд!")
            return

        # Обновляем время последней команды
        self.users[user_id] = current_time
        return await handler(event, data)