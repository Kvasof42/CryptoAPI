import os
from aiogram.filters import Filter
from aiogram import types
from dotenv import load_dotenv

load_dotenv()
ADMINS_ENV = os.getenv("ADMINS")

if not ADMINS_ENV:
    exit("Ошибка: Переменная ADMINS не найдена в файле .env!")

try:
    ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMINS_ENV.split(",")]
except ValueError:
    exit("Ошибка: Переменная ADMINS должна содержать только числа, разделенные запятыми.")

class IsAdmin(Filter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id in ADMIN_IDS