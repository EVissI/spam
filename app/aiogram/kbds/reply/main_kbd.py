from typing import Dict
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from loguru import logger

from app.db.models import User


class MainKeyboard:
    __user_kb_texts_dict = {
        "add_account_tdata": "Добавить аккаунт по tdata",
        "add_account_api": "Добавить аккаунт по api",
        "create_preset": "Добавить пресет",
        "my_accounts": "Мои аккаунты",
    }

    @staticmethod
    def get_user_kb_texts() -> Dict[str, str]:
        return MainKeyboard.__user_kb_texts_dict


    @staticmethod
    def build_main_kb() -> ReplyKeyboardMarkup:
        kb = ReplyKeyboardBuilder()

        for val in MainKeyboard.get_user_kb_texts().values():
            kb.button(text=val)

        kb.adjust(
            
        )

        return kb.as_markup(resize_keyboard=True)