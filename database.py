import asyncpg

async def create_pool():
    return await asyncpg.create_pool(
        user="postgres",
        password="postgres",
        host="localhost",
        database="postgres",
        min_size=1,
        max_size=10
    )

async def add_price(currency_id, price, pool):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO prices (currency_id, price) VALUES ($1, $2)",
            currency_id, price
        )

async def get_latest_price(symbol, pool=None):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT currencies.symbol, prices.price, prices.created_at
            FROM prices
            INNER JOIN currencies ON prices.currency_id = currencies.id
            WHERE currencies.symbol = $1
            ORDER BY prices.created_at DESC LIMIT 1
            """, symbol
        )

async def get_price_history(symbol, pool):
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT currencies.symbol, prices.price, prices.created_at
            FROM prices
            INNER JOIN currencies ON prices.currency_id = currencies.id
            WHERE currencies.symbol = $1
            ORDER BY prices.created_at DESC
            """, symbol
        )

async def add_subscription(telegram_id, currency_id, target_price, pool):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO subscriptions (telegram_id, currency_id, target_price)
            VALUES ($1, $2, $3)
            ON CONFLICT (telegram_id, currency_id) 
            DO UPDATE SET target_price = $3
            """, telegram_id, currency_id, target_price
        )

async def get_currencies(pool):
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT id, symbol FROM currencies")

async def get_currency_by_symbol(symbol, pool):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM currencies WHERE symbol = $1", symbol)

async def get_subscriptions_by_currency(currency_id, pool):
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT subscriptions.id, subscriptions.telegram_id, subscriptions.target_price, currencies.symbol AS currency_symbol
            FROM subscriptions
            INNER JOIN currencies ON subscriptions.currency_id = currencies.id
            WHERE subscriptions.currency_id = $1
            """, currency_id
        )

async def delete_user_subscription_by_symbol(telegram_id, symbol, pool):
    async with pool.acquire() as conn:
        currency = await conn.fetchrow("SELECT id FROM currencies WHERE symbol = $1", symbol)
        if not currency:
            return False
        
        result = await conn.execute(
            """
            DELETE FROM subscriptions 
            WHERE telegram_id = $1 AND currency_id = $2
            """, 
            telegram_id, currency["id"]
        )
        
        return result != "DELETE 0"
        
        
async def get_user_subscriptions(telegram_id, pool):
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT s.target_price, c.symbol 
            FROM subscriptions s
            INNER JOIN currencies c ON s.currency_id = c.id
            WHERE s.telegram_id = $1
            """, telegram_id
        )
        
        
async def add_currency(name, symbol, pool):
    async with pool.acquire() as conn:
        await conn.execute (
            """
            INSERT INTO currencies (name, symbol)
            VALUES ($1, $2)
            """, name, symbol
        )