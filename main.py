import aiosqlite
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.filters.state import State, StatesGroup, StateFilter
from aiogram import F
from aiogram.fsm.context import FSMContext
import json

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Замените "YOUR_BOT_TOKEN" на токен, который вы получили от BotFather
API_TOKEN = 'Token'

# Объект бота
bot = Bot(token=API_TOKEN)
# Диспетчер
dp = Dispatcher()

# Зададим имя базы данных
DB_NAME = 'quiz_bot.db'

with open('quiz_data.json', 'r', encoding='utf-8') as f:
    quiz_data = json.load(f)

def generate_options_keyboard(answer_options, right_answer):
    builder = InlineKeyboardBuilder()

    for option in answer_options:
        builder.add(types.InlineKeyboardButton(
            text=option,
            callback_data="right_answer" if option == right_answer else "wrong_answer")
        )

    builder.adjust(1)
    return builder.as_markup()

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

# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать игру"))
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))

async def get_question(message, user_id):
    # Получение текущего вопроса из словаря состояний пользователя
    current_question_index = await get_quiz_index(user_id)
    correct_index = quiz_data[current_question_index]['correct_option']
    opts = quiz_data[current_question_index]['options']
    kb = generate_options_keyboard(opts, opts[correct_index])
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)

@dp.message(F.text == "Начать игру")
async def new_quiz(message: types.Message):
    user_id = message.from_user.id
    current_question_index = 0
    await update_quiz_index(user_id, current_question_index)
    await reset_correct_answers(user_id)
    await reset_user_answers(user_id)
    await get_question(message, user_id)

async def finish_quiz(message, user_id):
    # Получаем количество правильных ответов для данного пользователя из базы данных
    correct_answers = await get_correct_answers(user_id)
    await message.answer(f"Квиз завершен! Вы ответили правильно на {correct_answers} из {len(quiz_data)} вопросов.")

    # Получаем и выводим ответы пользователя
    user_answers = await get_user_answers(user_id)
    answers_text = "\n".join([f"Вопрос {idx + 1}:\n {quiz_data[idx]['question']} - {'Правильно✅' if ans else 'Неправильно❌'}" for idx, ans in enumerate(user_answers)])
    await message.answer(f"Ваши ответы:\n{answers_text}")

    # Сохранение результата квиза
    await save_quiz_result(user_id, correct_answers, len(quiz_data))

async def get_quiz_index(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT current_question_index FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            else:
                # Если пользователя нет в базе, добавляем его
                await db.execute('INSERT INTO users (user_id, current_question_index, correct_answers) VALUES (?, ?, ?)', (user_id, 0, 0))
                await db.commit()
                return 0

async def update_quiz_index(user_id, current_question_index):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET current_question_index = ? WHERE user_id = ?', (current_question_index, user_id))
        await db.commit()

async def get_correct_answers(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT correct_answers FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            else:
                return 0

async def increment_correct_answers(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET correct_answers = correct_answers + 1 WHERE user_id = ?', (user_id,))
        await db.commit()

async def reset_correct_answers(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET correct_answers = 0 WHERE user_id = ?', (user_id,))
        await db.commit()

async def save_user_answer(user_id, question_index, is_correct):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO user_answers (user_id, question_index, is_correct) VALUES (?, ?, ?)', (user_id, question_index, is_correct))
        await db.commit()

async def get_user_answers(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT is_correct FROM user_answers WHERE user_id = ? ORDER BY question_index', (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def reset_user_answers(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM user_answers WHERE user_id = ?', (user_id,))
        await db.commit()

async def save_quiz_result(user_id, correct_answers, total_questions):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO quiz_results (user_id, correct_answers, total_questions) VALUES (?, ?, ?)', (user_id, correct_answers, total_questions))
        await db.commit()

@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT user_id, correct_answers, total_questions FROM quiz_results ORDER BY correct_answers DESC') as cursor:
            rows = await cursor.fetchall()
            stats_text = "\n".join([f"User {row[0]}: {row[1]} из {row[2]}" for row in rows])
            await message.answer(f"Статистика игроков:\n{stats_text}")

async def main():
    # Создаем базу данных
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                current_question_index INTEGER,
                correct_answers INTEGER
            )
        ''')
        await db.commit()

    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())