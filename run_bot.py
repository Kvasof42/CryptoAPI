import asyncio
import aiohttp
from handlers.bot import bot, dp
import scheduler
from database import create_pool
from aiogram.types import BotCommand

async def main():
    print("Запуск автономного бота и планировщика...")
    pool = await create_pool()
    session = aiohttp.ClientSession()

    bot.data = {
        "db_pool": pool,
        "http_session": session
    }

    await bot.set_my_commands([
        BotCommand(command="start", description="В начало"),
        BotCommand(command='help', description='Помощь'),
        BotCommand(command="list", description="Узнать какие есть валюты в боте"),
        BotCommand(command="price", description="Узнать цену валюты"),
        BotCommand(command="alert", description="Подписка на валюту"),
        BotCommand(command="subscriptions", description="Ваши подписки"),
        BotCommand(command="cancel", description="Отмена подписки")
    ])
    
    
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