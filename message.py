from database import *
from keyboard import generate_options_keyboard
import json

with open('quiz_data.json', 'r', encoding='utf-8') as f:
    quiz_data = json.load(f)


async def get_question(message, user_id):
    # Получение текущего вопроса из словаря состояний пользователя
    current_question_index = await get_quiz_index(user_id)
    correct_index = quiz_data[current_question_index]['correct_option']
    opts = quiz_data[current_question_index]['options']
    kb = generate_options_keyboard(opts, opts[correct_index])
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)

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