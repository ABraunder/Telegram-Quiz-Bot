import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import API_TOKEN
from database import create_db
from handlers import *

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)

dp.message.register(cmd_start, Command("start"))
dp.message.register(new_quiz, F.text == "Начать игру")
dp.callback_query.register(right_answer, F.data == "right_answer")
dp.callback_query.register(wrong_answer, F.data == "wrong_answer")
dp.message.register(show_stats, Command("stats"))

async def main():
    # Создаем базу данных
    await create_db()

    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())