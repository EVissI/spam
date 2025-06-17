import json
import os
from aiogram import Router, types, F
from aiogram.filters import StateFilter
from app.aiogram.kbds.inline.inine_kbd import AccountActionCallback, PresetSelectCallback, account_actions_keyboard, preset_select_keyboard
from app.aiogram.telethon_logic.utils import join_chats_with_intervals
from app.db.dao import AccountDAO, PresetDAO
from app.db.database import async_session_maker
from telethon import TelegramClient
from telethon.errors import RPCError
import asyncio

my_accounts_router = Router()
async def check_account_liquidity(account) -> bool:
    try:
        proxy = json.loads(account.proxy) if account.proxy else None
        client = TelegramClient(
            account.session_path,
            account.api_id,
            account.api_hash,
            proxy=(
                proxy["scheme"],
                proxy["hostname"],
                proxy["port"],
                proxy["username"],
                proxy["password"]
            ) if proxy else None
        )
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False
        await client.send_message("me", "Проверка")
        asyncio.create_task(delayed_disconnect(client, delay=10))
        return True
    except Exception:
        asyncio.create_task(delayed_disconnect(client, delay=10))
        return False

@my_accounts_router.message(F.text == "Мои аккаунты")
async def show_my_accounts(message: types.Message):
    user_id = message.from_user.id
    async with async_session_maker() as session:
        accounts = await AccountDAO.get_by_user_id(session, user_id)
    if not accounts:
        await message.answer("У вас нет добавленных аккаунтов.")
        return

    for acc in accounts:
        is_active = await check_account_liquidity(acc)
        status = "✅ Активен" if is_active else "❌ Неактивен"
        await message.answer(
            f"Телефон: <code>{acc.phone}</code>\n"
            f"Статус: {status}",reply_markup=account_actions_keyboard(account_id=acc.id)
        )

async def delayed_disconnect(client, delay: int = 10):
    await asyncio.sleep(delay)
    await client.disconnect()

@my_accounts_router.callback_query(AccountActionCallback.filter(F.action == "delete"))
async def delete_account_handler(callback: types.CallbackQuery, callback_data: AccountActionCallback):
    account_id = callback_data.account_id
    async with async_session_maker() as session:
        account = await AccountDAO.find_one_or_none_by_id(data_id=account_id, session=session)
        if not account:
            await callback.answer("Аккаунт не найден.", show_alert=True)
            return
        if account.session_path and os.path.exists(account.session_path):
            try:
                os.remove(account.session_path)
            except Exception as e:
                await callback.answer(f"Ошибка при удалении файла сессии: {e}", show_alert=True)
                return
        await AccountDAO.delete(session, id=account_id)
        await callback.message.edit_text("Аккаунт успешно удалён ✅")
        await callback.answer("Аккаунт удалён.")


@my_accounts_router.callback_query(AccountActionCallback.filter(F.action == "bind_preset"))
async def bind_preset_start(callback: types.CallbackQuery, callback_data: AccountActionCallback):
    account_id = callback_data.account_id
    async with async_session_maker() as session:
        presets = await PresetDAO.get_by_user_id(session, user_id=callback.from_user.id)
    if not presets:
        await callback.answer("У вас нет пресетов.", show_alert=True)
        return
    await callback.message.edit_text(
        "Выберите пресет для привязки:",
        reply_markup=preset_select_keyboard(presets, account_id)
    )
    await callback.answer()

@my_accounts_router.callback_query(PresetSelectCallback.filter())
async def bind_preset_finish(callback: types.CallbackQuery, callback_data: PresetSelectCallback, bot: types.Bot):
    account_id = callback_data.account_id
    preset_id = callback_data.preset_id
    async with async_session_maker() as session:
        await AccountDAO.set_preset(session, account_id, preset_id)
        account = await AccountDAO.find_one_or_none_by_id(data_id=account_id, session=session)
        preset = await PresetDAO.find_one_or_none_by_id(data_id=preset_id, session=session)
    await callback.message.edit_text("Пресет успешно привязан к аккаунту ✅")
    await callback.answer("Пресет установлен.")

    if account and preset:
        asyncio.create_task(join_chats_with_intervals(account, preset, bot))