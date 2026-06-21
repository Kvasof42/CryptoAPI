import asyncio
import logging
from database import add_price, get_currencies
from scraper import get_price
from notification import check_alerts


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_single_currency(currency: dict, session, pool, bot):

    symbol = currency["symbol"]
    currency_id = currency["id"]
    
    try:

        data = await get_price(symbol, session)
        current_price = data["price"]
        

        await add_price(currency_id=currency_id, price=current_price, pool=pool)

        await check_alerts(currency_id=currency_id, current_price=current_price, bot=bot, pool=pool)
        
        logger.info(f"Успешно обработано: {symbol} -> {current_price}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке валюты {symbol}: {e}")

async def scheduler(pool, bot, session):
    logger.info("Планировщик успешно запущен.")
    
    while True:
        try:

            currencies = await get_currencies(pool=pool)
            
            if not currencies:
                logger.warning("Список валют в базе данных пуст.")
            else:

                tasks = [
                    process_single_currency(currency, session, pool, bot) 
                    for currency in currencies
                ]

                await asyncio.gather(*tasks)
                
        except Exception as e:
            logger.critical(f"Критическая ошибка в главном цикле планировщика: {e}")


        await asyncio.sleep(300)