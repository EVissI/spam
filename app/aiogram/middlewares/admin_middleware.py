from typing import Callable, Any, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from app.config import settings

class CheckAdmin(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if event.from_user.id not in settings.ADMIN_IDS:
            await event.answer("У вас нет прав для выполнения этой команды.")
            return
            
        return await handler(event, data)