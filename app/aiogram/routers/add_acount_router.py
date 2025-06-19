import asyncio
import json
import random
import socks
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter
from app.aiogram.kbds.reply.main_kbd import MainKeyboard
from app.aiogram.utils import delayed_disconnect, parse_proxy, save_account_to_db
from app.db.dao import UserDAO
from app.db.models import Accounts
from app.db.shemas import UserModel
from app.db.database import async_session_maker
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
)
import os

add_account_router = Router()

class AddAccountState(StatesGroup):
    waiting_for_account_data = State()
    waiting_for_proxy = State()
    waiting_for_code = State()
    waiting_for_password = State()


def generate_android_device_params():
    device_models = [
        "Samsung Galaxy S23",
        "Xiaomi 13 Pro",
        "Google Pixel 8 Pro",
        "OnePlus 11",
        "Realme GT Neo 5",
        "Vivo X90 Pro",
    ]
    android_versions = ["Android 14", "Android 13", "Android 12", "Android 11"]
    app_versions = [
        "11.12.0",
        "11.11.0",
        "11.9.1",
        "11.8.3",
        "11.8.1",
        "11.7.4",
        "11.7.2",
        "11.6.2",
        "11.5.5",
        "11.5.3",
    ]
    return {
        "device_model": random.choice(device_models),
        "system_version": random.choice(android_versions),
        "app_version": random.choice(app_versions),
        "system_lang_code": "ru",
        "lang_code": "ru",
    }


def get_session_name(phone: str) -> str:
    return f"session_{phone.replace('+', '').replace(' ', '')}"


def parse_account_data(text: str):
    parts = text.split(":")
    if len(parts) != 3 or not parts[0].isdigit() or not parts[2].startswith("+"):
        return None
    api_id, api_hash, phone = parts
    return int(api_id), api_hash, phone


@add_account_router.message(F.text == MainKeyboard.get_user_kb_texts()["add_account_api"])
async def ask_account_data(message: types.Message, state: FSMContext):
    await message.answer(
        "Отправьте данные аккаунта в формате:\n<code>api_id:api_hash:номер_телефона</code>\n"
        "Пример: <code>123456:abcdef1234567890:+79991234567</code>"
    )
    await state.set_state(AddAccountState.waiting_for_account_data)


@add_account_router.message(
    F.text, StateFilter(AddAccountState.waiting_for_account_data)
)
async def ask_proxy(message: types.Message, state: FSMContext):
    parsed = parse_account_data(message.text)
    if not parsed:
        await message.answer("Неверный формат. Попробуйте снова.")
        return
    api_id, api_hash, phone = parsed
    await state.update_data(api_id=api_id, api_hash=api_hash, phone=phone)
    await message.answer(
        "Отправьте прокси в формате <code>socks5://user:pass@host:port</code> или <code>-</code> если прокси не требуется."
    )
    await state.set_state(AddAccountState.waiting_for_proxy)


@add_account_router.message(F.text, StateFilter(AddAccountState.waiting_for_proxy))
async def process_account_with_proxy(message: types.Message, state: FSMContext):
    data = await state.get_data()
    api_id = data["api_id"]
    api_hash = data["api_hash"]
    phone = data["phone"]
    proxy_str = message.text.strip()
    if proxy_str == "-":
        proxy = None
        proxy_str = None
    else:
        proxy = parse_proxy(proxy_str)
    session_name = get_session_name(phone)
    session_path = f"sessions/{session_name}.session"
    os.makedirs("sessions", exist_ok=True)
    device_params = generate_android_device_params()
    client_kwargs = dict(
        session=session_path, api_id=api_id, api_hash=api_hash, **device_params
    )
    if proxy:
        proxy_tuple = (
            socks.SOCKS5,
            proxy["hostname"],
            proxy["port"],
            True,
            proxy["username"],
            proxy["password"],
        )
        client_kwargs["proxy"] = proxy_tuple
    client = TelegramClient(**client_kwargs)
    await client.connect()
    await state.update_data(
        session_path=session_path, device_params=device_params, proxy=proxy_str
    )
    if not await client.is_user_authorized():
        result = await client.send_code_request(phone)
        await state.update_data(phone_code_hash=result.phone_code_hash)
        await message.answer("Введите код, который пришёл в Telegram:")
        await state.set_state(AddAccountState.waiting_for_code)
        return
    asyncio.create_task(delayed_disconnect(client, delay=10))
    await message.answer("Аккаунт уже был добавлен ранее!")
    await state.clear()


@add_account_router.message(F.text, StateFilter(AddAccountState.waiting_for_code))
async def process_code(message: types.Message, state: FSMContext):
    data = await state.get_data()
    api_id = data["api_id"]
    api_hash = data["api_hash"]
    phone = data["phone"]
    session_path = data["session_path"]
    device_params = data["device_params"]
    proxy_str = data.get("proxy")
    proxy = parse_proxy(proxy_str) if proxy_str else None
    phone_code_hash = data.get("phone_code_hash")  
    client_kwargs = dict(
        session=session_path, api_id=api_id, api_hash=api_hash, **device_params
    )
    if proxy:
        proxy_tuple = (
            socks.SOCKS5,
            proxy["hostname"],
            proxy["port"],
            True,
            proxy["username"],
            proxy["password"],
        )
        client_kwargs["proxy"] = proxy_tuple
    client = TelegramClient(**client_kwargs)
    await client.connect()
    code = message.text.strip()
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
    except SessionPasswordNeededError:
        await message.answer("Установлен двухфакторный пароль. Введите пароль:")
        await state.set_state(AddAccountState.waiting_for_password)
        return
    except (PhoneCodeInvalidError, PhoneNumberInvalidError):
        await message.answer(
            "Ошибка: неверный код или номер телефона. Попробуйте снова."
        )
        await client.disconnect()
        await state.clear()
        return
    await client.send_message("me", "✅ Аккаунт успешно добавлен через бота!")
    asyncio.create_task(delayed_disconnect(client, delay=10))
    await save_account_to_db(
        user_id=message.from_user.id,
        api_id=api_id,
        api_hash=api_hash,
        phone=phone,
        session_path=session_path,
        proxy=proxy_str if proxy_str != "-" else None,
    )
    await message.answer("Аккаунт успешно добавлен и сохранён!")
    await state.clear()


@add_account_router.message(F.text, StateFilter(AddAccountState.waiting_for_password))
async def process_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    api_id = data["api_id"]
    api_hash = data["api_hash"]
    phone = data["phone"]
    session_path = data["session_path"]
    device_params = data["device_params"]
    proxy_str = data.get("proxy")
    proxy = parse_proxy(proxy_str) if proxy_str else None
    client_kwargs = dict(
        session=session_path, api_id=api_id, api_hash=api_hash, **device_params
    )
    if proxy:
        proxy_tuple = (
            socks.SOCKS5,
            proxy["hostname"],
            proxy["port"],
            True,
            proxy["username"],
            proxy["password"],
        )
        client_kwargs["proxy"] = proxy_tuple
    client = TelegramClient(**client_kwargs)
    await client.connect()
    password = message.text.strip()
    try:
        await client.sign_in(phone=phone, password=password)
    except Exception as e:
        await message.answer(f"Ошибка при вводе пароля: {e}")
        await client.disconnect()
        await state.clear()
        return
    await client.send_message("me", "✅")
    asyncio.create_task(delayed_disconnect(client, delay=10))
    await save_account_to_db(
        user_id=message.from_user.id,
        api_id=api_id,
        api_hash=api_hash,
        phone=phone,
        session_path=session_path,
        proxy=proxy_str if proxy_str != "-" else None,
    )
    await message.answer("Аккаунт успешно добавлен и сохранён!")
    await state.clear()


