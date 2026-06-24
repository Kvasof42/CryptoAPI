import os
from aiogram.filters import Filter
from aiogram import types
from dotenv import load_dotenv

load_dotenv()
ADMIN = os.getenv("ADMINS")

if not ADMIN:
    exit("Ошибка: Токен бота не найден в файле .env!")

class IsAdmin(Filter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id in ADMIN