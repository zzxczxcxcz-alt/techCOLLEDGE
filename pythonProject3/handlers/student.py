import datetime
import re
from aiogram import types
from aiogram.fsm.context import FSMContext
from db.database import cursor, conn
from fsm.states import Registration
from ui.keyboards import get_main_keyboard
from handlers import router


@router.message(commands=['check_attendance'])
async def check_attendance(message: types.Message):
    try:
        student_name = message.from_user.full_name  # Получаем имя студента (можно использовать ID или username)

        # Запрос в базу данных для проверки посещаемости
        cursor.execute('''
            SELECT status FROM attendance 
            WHERE student_name = ? AND date = DATE('now')
        ''', (student_name,))

        result = cursor.fetchone()

        if result is None or len(result) == 0:
            await message.answer("❌ У вас нет записей о посещаемости за сегодня.")
        elif result[0]:
            await message.answer(f"📅 Вы были на занятиях сегодня: {result[0]}.")
        else:
            await message.answer("⚠️ Ошибка чтения данных о посещаемости.")

    except Exception as e:
        print(e)
        await message.answer("Ошибка сервера при проверке посещаемости.")