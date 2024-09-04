import aiosqlite
from config import DB_NAME

async def create_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS quiz_results (
                user_id INTEGER PRIMARY KEY,
                correct_answers INTEGER,
                total_questions INTEGER
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_answers (
                user_id INTEGER,
                question_index INTEGER,
                is_correct BOOLEAN
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                current_question_index INTEGER,
                correct_answers INTEGER
            )
        ''')

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