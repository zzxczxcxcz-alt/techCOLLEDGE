import datetime
import re
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db.database import cursor, conn
from fsm.states import AddStudents, EditStudents
from ui.keyboards import get_back_keyboard, get_edit_students_keyboard
from handlers import router

# Добавление студентов
@router.message(lambda message: message.text == '👥 Добавить студентов')
async def add_students(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    cursor.execute("SELECT name, role, status FROM users WHERE telegram_id = ?", (telegram_id,))
    current = cursor.fetchone()
    
    if current is None or current[1] != 'curator' or current[2] != 'confirmed':
        await message.answer("❌ Доступ запрещён. Только подтверждённые кураторы могут добавлять студентов.")
        return
    
    # Получаем группы куратора
    cursor.execute('SELECT "group" FROM groupfromcurs WHERE name = ?', (current[0],))
    groups = [row[0] for row in cursor.fetchall()]
    
    if not groups:
        await message.answer("❌ У вас нет назначенных групп.")
        return
    
    # Создаем клавиатуру с группами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for group in groups:
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=group, callback_data=f"select_group_{group}")]
        )
    
    await message.answer(
        "🏷️ Выберите группу для добавления студентов:",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data and c.data.startswith('select_group_'))
async def process_select_group(callback: types.CallbackQuery, state: FSMContext):
    group = callback.data.split('_')[2]
    await state.update_data(group=group)
    
    await callback.message.answer(
        f"📝 Введите список студентов для группы {group}:\n\n"
        "• Каждого студента с новой строки\n"
        "• Формат: Фамилия Имя Отчество\n"
        "• Пример:\n"
        "Иванов Иван Иванович\n"
        "Петров Петр Петрович",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(AddStudents.students_list)
    await callback.answer()

@router.message(AddStudents.students_list)
async def process_students_list(message: types.Message, state: FSMContext):
    if message.text == '↩️ Назад':
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=types.ReplyKeyboardRemove())
        return
    
    data = await state.get_data()
    group = data['group']
    
    # Разбиваем на строки и очищаем
    students = [s.strip() for s in message.text.split('\n') if s.strip()]
    
    if not students:
        await message.answer("❌ Список студентов пуст. Введите снова:")
        return
    
    now = datetime.datetime.now()
    added_count = 0
    errors = []
    
    for student in students:
        if len(student) < 5:
            errors.append(f"❌ '{student}' - слишком короткое ФИО")
            continue
            
        # Проверяем, нет ли уже такого студента в группе
        cursor.execute(
            'SELECT id FROM users WHERE name = ? AND "group" = ? AND role = "student"',
            (student, group)
        )
        if cursor.fetchone():
            errors.append(f"⚠️ '{student}' - уже есть в группе")
            continue
            
        email = ''.join(c for c in student.lower() if c.isalnum()) + f'_{group}@college.edu'
        password = 'student123'
        
        try:
            cursor.execute('''
            INSERT INTO users (created_at, updated_at, name, email, password, role, "group", status)
            VALUES (?, ?, ?, ?, ?, 'student', ?, 'confirmed')
            ''', (now, now, student, email, password, group))
            added_count += 1
        except Exception as e:
            errors.append(f"❌ '{student}' - ошибка добавления")
    
    conn.commit()
    
    response = f"✅ В группу {group} добавлено {added_count} студентов"
    if errors:
        response += "\n\nОшибки:\n" + "\n".join(errors[:5])  # Показываем первые 5 ошибок
        if len(errors) > 5:
            response += f"\n... и ещё {len(errors) - 5} ошибок"
    
    await message.answer(response)
    await state.clear()

# Редактирование студентов
@router.message(lambda message: message.text == '✏️ Редактировать студентов')
async def edit_students(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    cursor.execute("SELECT name, role, status FROM users WHERE telegram_id = ?", (telegram_id,))
    current = cursor.fetchone()
    
    if current is None or current[2] != 'confirmed' or current[1] not in ['curator', 'headman']:
        await message.answer("❌ Доступ запрещён.")
        return
    
    # Получаем доступные группы
    if current[1] == 'curator':
        cursor.execute('SELECT "group" FROM groupfromcurs WHERE name = ?', (current[0],))
        groups = [row[0] for row in cursor.fetchall()]
    else:  # headman
        cursor.execute('SELECT headman_group FROM users WHERE telegram_id = ?', (telegram_id,))
        groups = [cursor.fetchone()[0]]
    
    if not groups:
        await message.answer("❌ У вас нет доступных групп.")
        return
    
    # Создаем клавиатуру с группами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for group in groups:
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=group, callback_data=f"edit_group_{group}")]
        )
    
    await message.answer(
        "🏷️ Выберите группу для редактирования:",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data and c.data.startswith('edit_group_'))
async def process_edit_group(callback: types.CallbackQuery, state: FSMContext):
    group = callback.data.split('_')[2]
    await state.update_data(group=group)
    
    # Показываем список студентов в группе
    cursor.execute(
        'SELECT name FROM users WHERE "group" = ? AND role = "student" AND status = "confirmed" ORDER BY name',
        (group,)
    )
    students = [row[0] for row in cursor.fetchall()]
    
    if students:
        students_list = "\n".join([f"• {student}" for student in students])
        response = f"👥 Студенты группы {group}:\n\n{students_list}"
    else:
        response = f"❌ В группе {group} нет студентов."
    
    await callback.message.answer(
        f"{response}\n\nВыберите действие:",
        reply_markup=get_edit_students_keyboard()
    )
    await state.set_state(EditStudents.action)
    await callback.answer()

@router.message(EditStudents.action)
async def process_edit_action(message: types.Message, state: FSMContext):
    action = message.text
    data = await state.get_data()
    group = data['group']
    
    if action == '↩️ Назад':
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=types.ReplyKeyboardRemove())
        return
    elif action == '👀 Показать список':
        cursor.execute(
            'SELECT name FROM users WHERE "group" = ? AND role = "student" ORDER BY name',
            (group,)
        )
        students = [row[0] for row in cursor.fetchall()]
        
        if students:
            students_list = "\n".join([f"• {student}" for student in students])
            response = f"👥 Студенты группы {group}:\n\n{students_list}"
        else:
            response = f"❌ В группе {group} нет студентов."
        
        await message.answer(response)
        return
    elif action == '✏️ Изменить студента':
        await message.answer(
            "✍️ Введите ФИО студента для изменения:",
            reply_markup=get_back_keyboard()
        )
        await state.set_state(EditStudents.student_name)
    elif action == '🗑️ Удалить студента':
        await message.answer(
            "🗑️ Введите ФИО студента для удаления:",
            reply_markup=get_back_keyboard()
        )
        await state.set_state(EditStudents.student_name)
    else:
        await message.answer("❌ Неизвестное действие. Выберите из меню.")

@router.message(EditStudents.student_name)
async def process_student_name(message: types.Message, state: FSMContext):
    if message.text == '↩️ Назад':
        await state.set_state(EditStudents.action)
        await message.answer("↩️ Возврат к выбору действия.", reply_markup=get_edit_students_keyboard())
        return
    
    student_name = message.text.strip()
    data = await state.get_data()
    group = data['group']
    previous_action = await state.get_data()
    
    # Проверяем существование студента
    cursor.execute(
        'SELECT id FROM users WHERE name = ? AND "group" = ? AND role = "student"',
        (student_name, group)
    )
    student = cursor.fetchone()
    
    if not student:
        await message.answer(f"❌ Студент '{student_name}' не найден в группе {group}. Введите снова:")
        return
    
    await state.update_data(student_name=student_name, student_id=student[0])
    
    # Определяем действие
    if 'action' in data and data.get('action') == '✏️ Изменить студента':
        await message.answer("✍️ Введите новое ФИО студента:")
        await state.set_state(EditStudents.new_name)
    else:  # Удаление
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_confirm_{student[0]}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="delete_cancel")]
        ])
        await message.answer(
            f"⚠️ Вы уверены, что хотите удалить студента '{student_name}' из группы {group}?",
            reply_markup=keyboard
        )

@router.message(EditStudents.new_name)
async def process_new_name(message: types.Message, state: FSMContext):
    if message.text == '↩️ Назад':
        await state.set_state(EditStudents.action)
        await message.answer("↩️ Возврат к выбору действия.", reply_markup=get_edit_students_keyboard())
        return
    
    new_name = message.text.strip()
    data = await state.get_data()
    
    if len(new_name) < 5:
        await message.answer("❌ Новое ФИО должно содержать не менее 5 символов. Введите снова:")
        return
    
    # Обновляем имя студента
    cursor.execute(
        'UPDATE users SET name = ?, updated_at = ? WHERE id = ?',
        (new_name, datetime.datetime.now(), data['student_id'])
    )
    conn.commit()
    
    await message.answer(f"✅ Студент переименован: '{data['student_name']}' → '{new_name}'")
    await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith('delete_confirm_'))
async def process_delete_confirm(callback: types.CallbackQuery):
    student_id = int(callback.data.split('_')[2])
    
    # Получаем данные студента перед удалением
    cursor.execute('SELECT name, "group" FROM users WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    
    if student:
        # Удаляем студента
        cursor.execute('DELETE FROM users WHERE id = ?', (student_id,))
        # Также удаляем связанные пропуски
        cursor.execute('DELETE FROM attendances WHERE student_name = ? AND "group" = ?', (student[0], student[1]))
        conn.commit()
        
        await callback.message.edit_text(f"✅ Студент '{student[0]}' удалён из группы {student[1]}")
    else:
        await callback.message.edit_text("❌ Студент не найден.")
    
    await callback.answer()

@router.callback_query(lambda c: c.data == 'delete_cancel')
async def process_delete_cancel(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Удаление отменено.")
    await callback.answer()