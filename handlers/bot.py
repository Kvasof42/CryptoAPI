import os
from aiogram import Bot, Dispatcher, F, types
from dotenv import load_dotenv
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import (add_subscription, get_currency_by_symbol, get_user_subscriptions,
delete_user_subscription_by_symbol, add_currency, get_currencies_paginated,
get_total_currencies, get_currencies, get_latest_price, get_price_history_limited)
from scraper import get_price
from filters import IsAdmin
import io
import matplotlib.pyplot as plt
from aiogram.types import BufferedInputFile

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    exit("Ошибка: Токен бота не найден в файле .env!")

bot = Bot(TOKEN)
dp = Dispatcher()

async def get_crypto_keyboard(pool):
    currencies = await get_currencies(pool)
    
    keyboard_buttons = []
    for currency in currencies:
        button = InlineKeyboardButton(
            text=f"{currency['symbol']}", 
            callback_data=f"price_{currency['symbol']}"
        )
        keyboard_buttons.append([button])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)



@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Бот мониторинга криптовалют\n\n"
        "Команды:\n"
        "/price - Узнать текущую цену\n"
        "/alert СИМВОЛ ЦЕНА - Создать уведомление\n"
        "Пример: /alert BTC 65000"
    )


@dp.message(Command("help"))
async def help_handler(message: types.Message):
    help_text = (
        "Доступные команды бота:\n\n"
        "Информация:\n\n"
        "/list - посмотреть список доступных для отслеживания монет.\n"
        "/price - посмотреть цену валюты.\n\n"
        "Подписки:\n\n"
        "/alert [символ] [цена] - установить уведомление, когда цена упадет до указанного порога.\n"
        "/subscriptions — список ваших активных ценовых уведомлений.\n"
        "/cancel [символ] - удалить подписку на уведомление для конкретной монеты."
    )
    await message.answer(help_text, parse_mode="Markdown")


@dp.message(Command("price"))
async def price_command(message: types.Message):
    pool = bot.data["db_pool"]
    keyboard = await get_crypto_keyboard(pool)
    await message.answer("Выберите монету для просмотра цены:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("price_"))
async def process_price_callback(callback: types.CallbackQuery):
    symbol = callback.data.split("_")[1]
    
    pool = bot.data["db_pool"]
    price_data = await get_latest_price(symbol, pool)
    
    if price_data:
        await callback.message.answer(f"{symbol}: {price_data['price']}$")
    else:
        await callback.message.answer("Данные по этой монете еще не загружены.")
    
    await callback.answer()


@dp.message(Command("alert"))
async def alert_cmd(message: Message):

    args = message.text.split()
    

    if len(args) != 3:
        await message.answer(
            "Неверный формат!\n"
            "Используйте: /alert СИМВОЛ ЦЕНА\n"
            "Пример: /alert BTC 62000"
        )
        return
    
    symbol = args[1].upper()
    raw_price = args[2].replace(",", ".")
    

    try:
        target_price = float(raw_price)
    except ValueError:
        await message.answer("Ошибка: Цена должна быть числом!")
        return
        

    pool = message.bot.data["db_pool"]
    

    currency = await get_currency_by_symbol(symbol, pool)
    if not currency:
        await message.answer(
            f"Валюта {symbol} не поддерживается.\n"
            f"Доступные: BTC, ETH, SOL"
        )
        return
        

    try:
        await add_subscription(
            telegram_id=message.from_user.id,
            currency_id=currency["id"],
            target_price=target_price,
            pool=pool
        )
        await message.answer(
            f"Уведомление успешно создано!\n"
            f"Монета: {symbol}\n"
            f"Бот напишет, если цена упадет до {target_price}$ или ниже."
        )
    except Exception as e:
        await message.answer("У вас уже есть активное уведомление на эту валюту.")
        
        
@dp.message(Command('subscriptions'))
async def list_subscriptions(message: Message):
    pool = message.bot.data["db_pool"]
    

    subscriptions = await get_user_subscriptions(message.from_user.id, pool)
    

    if not subscriptions:
        await message.answer("У вас пока нет активных подписок. Используйте команду /alert , чтобы добавить.")
        return


    text = "Ваши активные подписки:\n"
    for sub in subscriptions:
        text += f"{sub['symbol']} - порог: {sub['target_price']}$\n"
        
    await message.answer(text, parse_mode="Markdown")
    
    
@dp.message(Command('cancel'))
async def cancel_subscriptions(message: Message):
    args = message.text.split()
    
    if len(args) != 2:
        await message.answer(
            "Неверный формат.\n"
            "Используйте: /cancel BTC"
        )
        return
    
    symbol = args[1].upper()
    pool = message.bot.data["db_pool"]
    telegram_id = message.from_user.id
    
    try:
        was_deleted = await delete_user_subscription_by_symbol(telegram_id, symbol, pool)
        
        if was_deleted:
            await message.answer(f"Подписка на {symbol} успешно отменена!")
        else:
            await message.answer(f"Активная подписка на валюту {symbol} не найдена.")
            
    except Exception as e:
        print(f"Ошибка при удалении подписки: {e}")
        await message.answer("Произошла ошибка при отмене подписки. Попробуйте позже.")
        
        
        
@dp.message(Command("add_coin"), IsAdmin())
async def add_coin_handler(message: types.Message):
    args = message.text.split()
    
    if len(args) != 3:
        await message.answer(
            "Неверный формат!\n"
            "Пример: /add_coin Bitcoin BTC"
        )
        return
        
    name = args[1]
    symbol = args[2].upper()
    
    session = bot.data["http_session"]
    pool = bot.data["db_pool"]
    
    try:
        await get_price(symbol, session)
    except Exception:
        await message.answer(f"Ошибка: {symbol} не существует на бирже Binance.")
        return
        
    try:
        await add_currency(name, symbol, pool)
        await message.answer(f"Монета {name} ({symbol}) успешно добавлена в базу!")
    except Exception:
        await message.answer("Ошибка при добавлении. Возможно, монета или сокращение уже существуют.")
        
async def get_list_keyboard(page, total_pages):
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"list_{page-1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"list_{page+1}"))
    
    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None

@dp.message(Command("list"))
async def list_currencies(message: types.Message):
    await show_currencies(message, 1)

@dp.callback_query(F.data.startswith("list_"))
async def pagination_handler(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[1])
    await show_currencies(callback.message, page, is_callback=True)

async def show_currencies(message, page, is_callback=False):
    limit = 10
    offset = (page - 1) * limit
    
    pool = bot.data["db_pool"]
    currencies = await get_currencies_paginated(pool, limit, offset)
    total = await get_total_currencies(pool)
    total_pages = (total + limit - 1) // limit
    
    text = f"Список доступных монет (Страница {page}/{total_pages}):\n\n"
    for c in currencies:
        text += f"{c['name']} ({c['symbol']})\n"
    
    keyboard = await get_list_keyboard(page, total_pages)
    
    if is_callback:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)
        
        
        
@dp.message(Command("history"))
async def history_handler(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /history СИМВОЛ (например, /history BTC)")
        return

    symbol = args[1].upper()
    pool = message.bot.data["db_pool"]

    data = await get_price_history_limited(symbol, pool)
    
    if not data:
        await message.answer("Данные не найдены. Возможно, монета не существует или еще нет записей.")
        return

    prices = [float(row['price']) for row in reversed(data)]
    times = [row['created_at'].strftime("%H:%M") for row in reversed(data)]

    plt.figure(figsize=(10, 5))
    plt.plot(times, prices, marker='o', linestyle='-', color='b')
    plt.title(f"История цен {symbol} (последние 50 записей)")
    plt.xlabel("Время")
    plt.ylabel("Цена (USDT)")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    await message.answer_photo(
        photo=BufferedInputFile(buf.read(), filename="chart.png"),
        caption=f"График цен для {symbol}"
    )