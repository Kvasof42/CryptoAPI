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
    

    await asyncio.gather(
        scheduler.scheduler(pool=pool, bot=bot, session=session),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())