import asyncio

from app.aiogram.middlewares.admin_middleware import CheckAdmin
from app.aiogram.routers.init_router import init_router
from app.config import setup_logger

setup_logger("bot")
from loguru import logger
from app.config import bot, dp, admins

async def start_bot():
    for admin_id in admins:
        try:
            await bot.send_message(admin_id, f"Я запущен🥳.")
        except:
            pass
    logger.info("Бот успешно запущен.")


async def stop_bot():
    try:
        for admin_id in admins:
            await bot.send_message(admin_id, "Бот остановлен. За что?😔")
    except:
        pass
    logger.error("Бот остановлен!")


async def main():
    dp.message.middleware(CheckAdmin())
    dp.include_router(init_router)

    # регистрация функций
    dp.startup.register(start_bot)
    dp.shutdown.register(stop_bot)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
