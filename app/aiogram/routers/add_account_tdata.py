import asyncio
import os
import shutil
import zipfile
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter
from app.aiogram.kbds.reply.main_kbd import MainKeyboard
from app.aiogram.utils import parse_proxy, save_account_to_db
from app.db.dao import UserDAO
from app.db.models import Accounts
from app.db.shemas import UserModel
from app.db.database import async_session_maker
from telethon import TelegramClient
import socks
from opentele.td import TDesktop

add_tdata_router = Router()

class AddTDataState(StatesGroup):
    waiting_for_tdata = State()
    waiting_for_proxy = State()

def get_session_name_from_tdata(tdata_dir: str) -> str:
    return f"session_{os.path.basename(tdata_dir)}"


@add_tdata_router.message(F.text == MainKeyboard.get_user_kb_texts()["add_account_tdata"])
async def ask_tdata(message: types.Message, state: FSMContext):
    await message.answer(
        "Отправьте архив с папкой tdata (от Telegram Desktop) в виде файла.\n"
        "Формат: .zip или .rar. Размер архива не должен превышать лимит Telegram."
    )
    await state.set_state(AddTDataState.waiting_for_tdata)

@add_tdata_router.message(F.document, StateFilter(AddTDataState.waiting_for_tdata))
async def process_tdata_file(message: types.Message, state: FSMContext):
    file = message.document
    if not file.file_name.endswith((".zip", ".rar")):
        await message.answer("Пожалуйста, отправьте архив .zip или .rar с папкой tdata.")
        return

    uploads_dir = "uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    archive_path = os.path.join(uploads_dir, file.file_name)
    await file.download(destination=archive_path)

    extract_dir = os.path.join(uploads_dir, file.file_name + "_extracted")
    os.makedirs(extract_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
    except Exception as e:
        await message.answer(f"Ошибка при распаковке архива: {e}")
        shutil.rmtree(extract_dir, ignore_errors=True)
        os.remove(archive_path)
        return

    tdata_path = None
    for root, dirs, files in os.walk(extract_dir):
        if "tdata" in dirs:
            tdata_path = os.path.join(root, "tdata")
            break
    if not tdata_path:
        await message.answer("В архиве не найдена папка tdata.")
        shutil.rmtree(extract_dir, ignore_errors=True)
        os.remove(archive_path)
        return

    session_name = get_session_name_from_tdata(tdata_path)
    session_dir = "sessions"
    os.makedirs(session_dir, exist_ok=True)
    session_path = os.path.join(session_dir, f"{session_name}.session")

    try:
        TDesktop(tdata_path).convert_to_telethon_session(session_path)
    except Exception as e:
        await message.answer(f"Ошибка при конвертации tdata: {e}")
        shutil.rmtree(extract_dir, ignore_errors=True)
        os.remove(archive_path)
        return

    await state.update_data(
        session_path=session_path,
        tdata_extract_dir=extract_dir,
        archive_path=archive_path,
    )
    await message.answer(
        "Теперь отправьте строку прокси в формате:\n"
        "<code>socks5://user:pass@host:port</code>\n"
        "или <code>socks5://host:port</code>\n"
        "Если прокси не нужен — отправьте <b>-</b>"
    )
    await state.set_state(AddTDataState.waiting_for_proxy)

@add_tdata_router.message(F.text, StateFilter(AddTDataState.waiting_for_proxy))
async def process_proxy(message: types.Message, state: FSMContext):
    data = await state.get_data()
    session_path = data["session_path"]
    tdata_extract_dir = data["tdata_extract_dir"]
    archive_path = data["archive_path"]
    proxy_str = message.text.strip()
    proxy = parse_proxy(proxy_str)

    client_kwargs = dict(session=session_path, api_id=0, api_hash="")
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

    try:
        client = TelegramClient(**client_kwargs)
        await client.connect()
        if not await client.is_user_authorized():
            await message.answer("Сессия не авторизована. Проверьте tdata.")
            await client.disconnect()
            shutil.rmtree(tdata_extract_dir, ignore_errors=True)
            os.remove(archive_path)
            os.remove(session_path)
            await state.clear()
            return
        me = await client.get_me()
        await client.disconnect()
    except Exception as e:
        await message.answer(f"Ошибка при проверке сессии: {e}")
        shutil.rmtree(tdata_extract_dir, ignore_errors=True)
        os.remove(archive_path)
        os.remove(session_path)
        await state.clear()
        return

    await save_account_to_db(
        user_id=message.from_user.id,
        phone=me.phone if hasattr(me, "phone") else "",
        api_id=0,
        api_hash="",
        session_path=session_path,
        proxy=proxy_str if proxy_str != "-" else None,
    )

    await message.answer(
        f"✅ Аккаунт {me.first_name} успешно добавлен через tdata!\n"
        f"ID: <code>{me.id}</code>\n"
        f"Username: @{me.username if me.username else '—'}"
    )

    shutil.rmtree(tdata_extract_dir, ignore_errors=True)
    os.remove(archive_path)
    await state.clear()