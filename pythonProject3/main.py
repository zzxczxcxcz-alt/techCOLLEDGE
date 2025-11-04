import asyncio
import logging
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import bot
from db.database import init_db
from handlers import router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    try:
        init_db()

        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        dp.include_router(router)

        me = await bot.get_me()
        logger.info(f"Бот @{me.username} успешно запущен!")

        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")

if __name__ == '__main__':
    asyncio.run(main())

