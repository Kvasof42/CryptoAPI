import asyncio
import aiohttp
from handlers.bot import bot, dp
import scheduler
from database import create_pool

async def main():
    print("Запуск автономного бота и планировщика...")
    pool = await create_pool()
    session = aiohttp.ClientSession()

    bot.data = {
        "db_pool": pool,
        "http_session": session
    }

    try:
        await asyncio.gather(
            scheduler.scheduler(pool=pool, bot=bot, session=session),
            dp.start_polling(bot)
        )
    finally:
        await session.close()
        await pool.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")