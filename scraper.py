import aiohttp

async def get_price(symbol: str, session: aiohttp.ClientSession):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
    
    async with session.get(url) as response:
        if response.status != 200:
            raise Exception(f"Binance API error: {response.status}")
        data = await response.json()
        return {
            "symbol": symbol,
            "price": float(data["price"])
        }