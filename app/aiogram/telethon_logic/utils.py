import json
import random
import asyncio
import re
from datetime import datetime, timezone
from telethon import TelegramClient

MAX_MESSAGES_PER_DAY = 36
MIN_MSG_INTERVAL = 10 * 60
MAX_MSG_INTERVAL = 30 * 60
MIN_JOIN_INTERVAL = 20 * 60
MAX_JOIN_INTERVAL = 40 * 60


async def join_chats_with_intervals(account, preset, bot):
    proxy = json.loads(account.proxy) if account.proxy else None
    client = TelegramClient(
        account.session_path,
        account.api_id,
        account.api_hash,
        proxy=(
            (
                proxy["scheme"],
                proxy["hostname"],
                proxy["port"],
                proxy["username"],
                proxy["password"],
            )
            if proxy
            else None
        ),
    )
    await client.connect()
    try:
        if not await client.is_user_authorized():
            await client.disconnect()
            return

        joined_count = 0
        for chat_id in preset.target_chats:
            try:
                chat = await client.get_entity(chat_id)
                if getattr(chat, "kicked", False):
                    continue  # Пропускаем чат, если кикнуты
                elif getattr(chat, "left", False):
                    need_join = True
                else:
                    need_join = False
            except Exception:
                need_join = True

            if need_join:
                try:
                    await client.join_chat(chat_id)
                except Exception:
                    pass
                await asyncio.sleep(
                    random.randint(MIN_JOIN_INTERVAL, MAX_JOIN_INTERVAL)
                )
            joined_count += 1
            # После вступления в первые 2 чата запускаем рассылку
            if joined_count == 2:
                asyncio.create_task(
                    send_preset_messages(client, preset, bot, account.user_id)
                )

        # Если чатов меньше 2, всё равно запускаем рассылку после цикла
        if joined_count < 2:
            asyncio.create_task(
                send_preset_messages(client, preset, bot, account.user_id)
            )

        await bot.send_message(
            account.user_id,
            "✅ Вступление во все чаты завершено или запущена рассылка.",
        )
    except Exception as e:
        await bot.send_message(account.user_id, f"❌ Ошибка при вступлении в чаты: {e}")
        await client.disconnect()


async def send_preset_messages(client, preset, bot, user_id):
    try:
        messages_sent = 0
        last_reset = datetime.now(timezone.utc)
        while True:
            now = datetime.now(timezone.utc)
            if (now - last_reset).total_seconds() > 24 * 60 * 60:
                messages_sent = 0
                last_reset = now
            for chat_id in preset.target_chats:
                # Проверяем, состоит ли аккаунт в чате
                try:
                    chat = await client.get_entity(chat_id)
                    if getattr(chat, "kicked", False) or getattr(chat, "left", False):
                        continue  # Пропускаем, если кикнуты или не вступили
                except Exception:
                    continue  # Пропускаем, если не удалось получить чат

                if messages_sent >= MAX_MESSAGES_PER_DAY:
                    await asyncio.sleep(60 * 60)
                    continue
                sent = False
                attempt = 0
                while not sent and attempt < 3:
                    attempt += 1
                    msg = await client.send_message(chat_id, preset.message)
                    send_time = datetime.now(timezone.utc)
                    await asyncio.sleep(2)
                    channels_to_join = set()
                    async for reply in client.iter_messages(chat_id, limit=10):
                        # Проверяем только reply на наше сообщение и в течение 7 секунд после отправки
                        if (
                            reply.reply_to_msg_id == msg.id
                            and abs((send_time - reply.date).total_seconds()) < 7
                        ):
                            if reply.text and (
                                "необходимо подписаться" in reply.text.lower()
                                or "чтобы писать в чат" in reply.text.lower()
                            ):
                                # Ищем все @usernames и t.me ссылки
                                channels_to_join.update(
                                    re.findall(r"@(\w+)", reply.text)
                                )
                                channels_to_join.update(
                                    re.findall(r"https://t\.me/([\w+]+)", reply.text)
                                )
                    if channels_to_join:
                        success = True
                        for channel in channels_to_join:
                            try:
                                await client.join_chat(channel)
                                await asyncio.sleep(2)
                            except Exception:
                                success = False
                        if success:
                            continue  # Пробуем отправить снова
                        else:
                            break
                    sent = True
                    messages_sent += 1
                    await asyncio.sleep(
                        random.randint(MIN_MSG_INTERVAL, MAX_MSG_INTERVAL)
                    )
    except Exception as e:
        await bot.send_message(user_id, f"❌ Ошибка при рассылке: {e}")
        await client.disconnect()
