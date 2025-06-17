from aiogram import Router,F
from aiogram.types import Message
from aiogram.filters import CommandStart

from app.aiogram.kbds.reply.main_kbd import MainKeyboard
from app.db.dao import UserDAO
from app.db.database import async_session_maker
from app.db.shemas import UserModel


start_router = Router()

@start_router.message(CommandStart())
async def start_command_handler(message: Message):
    async with async_session_maker() as session:
        user = await UserDAO.find_one_or_none_by_id(message.from_user.id, session)
        if not user:
            await UserDAO.add(session,UserModel(
                id=message.from_user.id,
                username=message.from_user.username
            ))
        await message.answer("Привет! Я бот, который поможет тебе управлять твоими аккаунтами и пресетами. Выбери действие из меню ниже.", 
                             reply_markup=MainKeyboard.build_main_kb())