from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.filters.state import State, StatesGroup, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F
from aiogram.fsm.context import FSMContext
from database import *
from message import *
from config import API_TOKEN

dp = Dispatcher()
bot = Bot(token=API_TOKEN)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать игру"))
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))


@dp.message(F.text == "Начать игру")
async def new_quiz(message: types.Message):
    user_id = message.from_user.id
    current_question_index = 0
    await update_quiz_index(user_id, current_question_index)
    await reset_correct_answers(user_id)
    await reset_user_answers(user_id)
    await get_question(message, user_id)

@dp.callback_query(F.data == "right_answer")
async def right_answer(callback: types.CallbackQuery):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    
    current_question_index = await get_quiz_index(callback.from_user.id)
    # Обновление номера текущего вопроса в базе данных
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index)

    # Увеличиваем счетчик правильных ответов
    await increment_correct_answers(callback.from_user.id)

    # Сохранение ответа пользователя
    await save_user_answer(callback.from_user.id, current_question_index - 1, True)

    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        await finish_quiz(callback.message, callback.from_user.id)

@dp.callback_query(F.data == "wrong_answer")
async def wrong_answer(callback: types.CallbackQuery):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )

    # Получение текущего вопроса из словаря состояний пользователя
    current_question_index = await get_quiz_index(callback.from_user.id)
    correct_option = quiz_data[current_question_index]['correct_option']

    # Обновление номера текущего вопроса в базе данных
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index)

    # Сохранение ответа пользователя
    await save_user_answer(callback.from_user.id, current_question_index - 1, False)

    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        await finish_quiz(callback.message, callback.from_user.id)

@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT user_id, correct_answers, total_questions FROM quiz_results ORDER BY correct_answers DESC') as cursor:
            rows = await cursor.fetchall()
            stats_text = "\n".join([f"{await get_username(row[0])}: {row[1]} из {row[2]}" for row in rows])
            await message.answer(f"Статистика игроков:\n{stats_text}")

async def get_username(user_id: int) -> str:
    chat = await bot.get_chat(user_id)
    return chat.first_name