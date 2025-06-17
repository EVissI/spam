from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter
from app.aiogram.kbds.reply.main_kbd import MainKeyboard
from app.db.dao import PresetDAO
from app.db.models import Presets
from app.db.database import async_session_maker
from app.db.shemas import PresetsModel

add_preset_router = Router()


class CreatePreset(StatesGroup):
    waiting_for_chats = State()
    waiting_for_message = State()
    waiting_for_name = State()


async def resolve_chat_ids(bot: Bot, chat_links: list[str]) -> list[int]:
    chat_ids = []
    for link in chat_links:
        chatname = link.strip()
        if chatname.startswith("https://t.me/"):
            chatname = chatname.replace("https://t.me/", "")
        if chatname.startswith("@"):
            chatname = chatname[1:]
        try:
            chat = await bot.get_chat(chatname)
            chat_ids.append(chat.id)
        except Exception:
            pass
    return chat_ids


@add_preset_router.message(F.text == MainKeyboard.get_user_kb_texts()["create_preset"])
async def start_create_preset(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите ссылки или username чатов через запятую (например, @chat1, https://t.me/chat2):"
    )
    await state.set_state(CreatePreset.waiting_for_chats)


@add_preset_router.message(F.text, StateFilter(CreatePreset.waiting_for_chats))
async def get_chats(message: types.Message, state: FSMContext, bot: Bot):
    chat_links = [i.strip() for i in message.text.split(",") if i.strip()]
    chat_ids = await resolve_chat_ids(bot, chat_links)
    if not chat_ids:
        await message.answer(
            "Не удалось определить ни одного чата. Проверьте ссылки/юзернеймы."
        )
        return
    await state.update_data(target_chats=chat_ids)
    await message.answer("Введите текст сообщения:")
    await state.set_state(CreatePreset.waiting_for_message)


@add_preset_router.message(F.text, StateFilter(CreatePreset.waiting_for_message))
async def get_message(message: types.Message, state: FSMContext):
    await state.update_data(message_text=message.text)
    await message.answer("Введите название пресета:")
    await state.set_state(CreatePreset.waiting_for_name)


@add_preset_router.message(F.text, StateFilter(CreatePreset.waiting_for_name))
async def get_preset_name(message: types.Message, state: FSMContext):
    await state.update_data(preset_name=message.text)
    data = await state.get_data()
    user_id = message.from_user.id

    async with async_session_maker() as session:
        await PresetDAO.add(
            session,
            PresetsModel(
                preset_name=data["preset_name"],
                message=data["message_text"],
                target_chats=data["target_chats"],
                user_id=user_id,
            ),
        )

    await message.answer("Пресет успешно создан!")
    await state.clear()
