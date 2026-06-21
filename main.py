from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from decimal import Decimal
import asyncio
import aiohttp
import scheduler
from handlers.bot import bot, dp
from database import create_pool, get_latest_price, get_price_history
from datetime import datetime

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Запуск сервера...")
    

    pool = await create_pool()

    
    app.state.pool = pool

    
    yield
    
    print("Остановка сервера...")

    await pool.close()

app = FastAPI(lifespan=lifespan)

class CryptoSchema(BaseModel):
    symbol: str
    price: Decimal
    created_at: datetime

@app.get('/prices/{symbol}/latest', response_model=CryptoSchema)
async def read_latest_price(symbol: str):
    result = await get_latest_price(symbol.upper())
    if not result:
        raise HTTPException(status_code=404, detail="Currency not found")
    return result
    
@app.get('/prices/{symbol}/history', response_model=list[CryptoSchema])
async def read_price_history(symbol: str):
    result = await get_price_history(symbol.upper())
    if not result:
        raise HTTPException(status_code=404, detail="Currency not found")
    return result