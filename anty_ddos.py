import asyncio
import logging
from aiogram import  types
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from anyio import current_time


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit: float = 2.0):
        super().__init__()
        self.limit = limit
        self.users = {}

    async def __call__(self, handler, event: types.Message, data):
        user_id = event.from_user.id
        current_time = asyncio.get_event_loop().time()

        # Если пользователь уже отправлял команду недавно
        if user_id in self.users and (current_time - self.users[user_id]) < self.limit:
            logging.warning(f"Пользователь {user_id} превышает лимит команд!")
            return

        # Обновляем время последней команды
        self.users[user_id] = current_time
        return await handler(event, data)