from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData

class AccountActionCallback(CallbackData, prefix="account_action"):
    action: str
    account_id: int

def account_actions_keyboard(account_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text="Привязать пресет",
        callback_data=AccountActionCallback(action="bind_preset", account_id=account_id).pack(),
    )
    kb.button(
        text="Удалить аккаунт",
        callback_data=AccountActionCallback(action="delete", account_id=account_id).pack(),
    )
    return kb.as_markup()

class PresetSelectCallback(CallbackData, prefix="preset_select"):
    preset_id: int
    account_id: int

def preset_select_keyboard(presets, account_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for preset in presets:
        kb.button(
            text=preset.preset_name,
            callback_data=PresetSelectCallback(preset_id=preset.id, account_id=account_id).pack()
        )
    return kb.as_markup()