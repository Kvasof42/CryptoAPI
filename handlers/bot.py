import os
from aiogram import Bot, Dispatcher, F
from dotenv import load_dotenv
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import add_subscription, get_currency_by_symbol, get_user_subscriptions, delete_user_subscription_by_symbol, add_currency
from scraper import get_price
from filters import IsAdmin


load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    exit("Ошибка: Токен бота не найден в файле .env!")

bot = Bot(TOKEN)
dp = Dispatcher()


crypto_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Bitcoin (BTC)", callback_data="price_BTC")],
        [InlineKeyboardButton(text="Ethereum (ETH)", callback_data="price_ETH")],
        [InlineKeyboardButton(text="Solana (SOL)", callback_data="price_SOL")]
    ]
)

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Бот мониторинга криптовалют\n\n"
        "Команды:\n"
        "/price - Узнать текущую цену\n"
        "/alert СИМВОЛ ЦЕНА - Создать уведомление\n"
        "Пример: /alert BTC 65000"
    )

@dp.message(Command("price"))
async def price_cmd(message: Message):
    await message.answer("Выберите валюту для проверки цены:", reply_markup=crypto_inline_keyboard)

# Хэндлер, который ловит нажатия на кнопки цен
@dp.callback_query(F.data.startswith("price_"))
async def process_price_callback(callback: CallbackQuery):
    symbol = callback.data.split("_")[1]
    

    session = callback.bot.data["http_session"]
    
    try:
        data = await get_price(symbol, session)
        await callback.message.edit_text(
            f"{symbol}\nТекущая цена: {data['price']}$",
            reply_markup=crypto_inline_keyboard
        )
    except Exception as e:
        await callback.message.answer(f"Ошибка при запросе к Binance: {e}")
    
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
        
        
@dp.message(Command('list'))
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
        
        
        
@dp.message(Command('add_coin'), IsAdmin())
async def added_currency(message: Message):
    args = message.text.split()
    
    if len(args) != 3:
        await message.answer(
            "Неверный формат!\n"
            "Используйте другую форму\n"
            "Пример: /add_coin [название_монеты] [сокращение монеты, пример BTC]"
        )
        return
    
    currency_name = args[1].lower().capitalize()
    currency_symbol = args[2].upper()
    pool = message.bot.data.get('dp_pool')
    if not pool:
        await message.answer('Ошибка')
        
    try:
        await add_currency(
            name=currency_name,
            symbol=currency_symbol,
            pool=pool
        )
        await message.answer(
            f'Монета успешно добавлена\n',
            f'Название: {currency_name}\n',
            f'Тикер: {currency_symbol}'
        )
    except Exception as e:
        await message.answer(f"Ошибка при добавлении монеты. Возможно, она уже существует.")
        print(f"Ошибка в /add_coin: {e}")