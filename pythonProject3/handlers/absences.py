import datetime
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db.database import cursor, conn
from fsm.states import AddAbsence
from ui.keyboards import get_back_keyboard
from handlers import router

@router.message(lambda message: message.text == '📝 Добавить пропуски')
async def add_absence(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    cursor.execute("SELECT id, name, role, headman_group, status FROM users WHERE telegram_id = ?", (telegram_id,))
    current = cursor.fetchone()
    
    if current is None or current[4] != 'confirmed' or current[2] not in ['headman', 'curator']:
        await message.answer("❌ Доступ запрещён.")
        return
        
    allowed_groups = []
    if current[2] == 'headman':
        allowed_groups = [current[3]]
    elif current[2] == 'curator':
        cursor.execute('SELECT "group" FROM groupfromcurs WHERE name = ?', (current[1],))
        allowed_groups = [row[0] for row in cursor.fetchall()]
        
    if not allowed_groups:
        await message.answer("❌ Нет доступных групп.")
        return
        
    # Создаем клавиатуру с группами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for group in allowed_groups:
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=group, callback_data=f"abs_group_{group}")]
        )
        
    await message.answer("🏷️ Выберите группу:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data and c.data.startswith('abs_group_'))
async def process_abs_group(callback: types.CallbackQuery, state: FSMContext):
    group = callback.data.split('_')[2]
    await state.update_data(group=group)
    
    # Получаем студентов группы
    cursor.execute(
        'SELECT id, name FROM users WHERE "group" = ? AND role = "student" AND status = "confirmed" ORDER BY name',
        (group,)
    )
    students = cursor.fetchall()
    
    if not students:
        await callback.message.answer(f"❌ В группе {group} нет студентов.")
        await callback.answer()
        return
        
    # Создаем клавиатуру со студентами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for student in students:
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=student[1], callback_data=f"abs_student_{student[0]}")]
        )
        
    await callback.message.answer("👥 Выберите студента:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith('abs_student_'))
async def process_abs_student(callback: types.CallbackQuery, state: FSMContext):
    student_id = int(callback.data.split('_')[2])
    cursor.execute('SELECT name, "group" FROM users WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    
    if not student:
        await callback.message.answer("❌ Студент не найден.")
        await callback.answer()
        return
        
    await state.update_data(student_id=student_id, student_name=student[0], group=student[1])
    
    await callback.message.answer(
        f"⏰ Введите количество пропущенных часов/занятий для {student[0]}:",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(AddAbsence.hours)
    await callback.answer()

@router.message(AddAbsence.hours)
async def process_hours(message: types.Message, state: FSMContext):
    if message.text == '↩️ Назад':
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=types.ReplyKeyboardRemove())
        return
        
    try:
        hours = int(message.text)
        if hours <= 0:
            await message.answer("❌ Введите положительное число:")
            return
        if hours > 100:
            await message.answer("❌ Слишком большое количество часов. Введите снова:")
            return
    except ValueError:
        await message.answer("❌ Введите число:")
        return
        
    await state.update_data(hours=hours)
    
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text='✅ Уважительная'), types.KeyboardButton(text='❌ Неуважительная')],
            [types.KeyboardButton(text='↩️ Назад')]
        ],
        resize_keyboard=True
    )
    await message.answer("📋 Выберите причину пропуска:", reply_markup=keyboard)
    await state.set_state(AddAbsence.reason)

@router.message(AddAbsence.reason)
async def process_reason(message: types.Message, state: FSMContext):
    if message.text == '↩️ Назад':
        await state.set_state(AddAbsence.hours)
        await message.answer("⏰ Введите количество часов:", reply_markup=get_back_keyboard())
        return
        
    reason_text = message.text
    if reason_text == '✅ Уважительная':
        reason = 'ув'
        reason_display = 'уважительная'
    elif reason_text == '❌ Неуважительная':
        reason = 'неув'
        reason_display = 'неуважительная'
    else:
        await message.answer("❌ Выберите причину из предложенных вариантов:")
        return
        
    await state.update_data(reason=reason, reason_display=reason_display)
    
    await message.answer(
        "📝 Введите описание/причину пропуска (или нажмите 'Пропустить'):",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text='⏭️ Пропустить')], [types.KeyboardButton(text='↩️ Назад')]],
            resize_keyboard=True
        )
    )
    await state.set_state(AddAbsence.description)

@router.message(AddAbsence.description)
async def process_description(message: types.Message, state: FSMContext):
    if message.text == '↩️ Назад':
        await state.set_state(AddAbsence.reason)
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text='✅ Уважительная'), types.KeyboardButton(text='❌ Неуважительная')],
                [types.KeyboardButton(text='↩️ Назад')]
            ],
            resize_keyboard=True
        )
        await message.answer("📋 Выберите причину пропуска:", reply_markup=keyboard)
        return
        
    description = message.text if message.text != '⏭️ Пропустить' else ''
    
    data = await state.get_data()
    student_name = data['student_name']
    group = data['group']
    hours = data['hours']
    reason = data['reason']
    reason_display = data['reason_display']
    
    date = datetime.date.today().isoformat()
    telegram_id = message.from_user.id
    
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    creator_result = cursor.fetchone()
    created_by = creator_result[0] if creator_result else None
    
    now = datetime.datetime.now()
    
    try:
        cursor.execute('''
        INSERT INTO attendances (created_at, updated_at, student_name, "group", date, hours_missed, reason, description, created_by, subject, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', 'active')
        ''', (now, now, student_name, group, date, hours, reason, description, created_by))
        
        conn.commit()
        
        # Показываем статистику студента
        cursor.execute('''
        SELECT 
            SUM(hours_missed) as total,
            SUM(CASE WHEN reason = 'ув' THEN hours_missed ELSE 0 END) as excused
        FROM attendances 
        WHERE student_name = ? AND "group" = ?
        ''', (student_name, group))
        
        stats = cursor.fetchone()
        total_hours = stats[0] or 0
        excused_hours = stats[1] or 0
        
        response = (
            f"✅ Пропуски добавлены!\n\n"
            f"👤 Студент: {student_name}\n"
            f"🏷️ Группа: {group}\n"
            f"⏰ Пропущено: {hours} часов\n"
            f"📋 Причина: {reason_display}\n"
            f"📝 Описание: {description if description else 'не указано'}\n\n"
            f"📊 Общая статистика студента:\n"
            f"• Всего пропусков: {total_hours} часов\n"
            f"• Уважительных: {excused_hours} часов\n"
            f"• Неуважительных: {total_hours - excused_hours} часов"
        )
        
        await message.answer(response, reply_markup=types.ReplyKeyboardRemove())
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении пропусков: {e}")
    
    await state.clear()