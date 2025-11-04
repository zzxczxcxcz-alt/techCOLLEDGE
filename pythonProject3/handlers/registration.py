import datetime
import re
from aiogram import types
from aiogram.fsm.context import FSMContext
from db.database import cursor, conn
from fsm.states import Registration
from ui.keyboards import get_main_keyboard
from handlers import router

@router.message(Registration.role)
async def process_role(message: types.Message, state: FSMContext):
    role_text = message.text
    if role_text == '👨‍🎓 Староста':
        role = 'headman'
    elif role_text == '👨‍🏫 Куратор':
        role = 'curator'
    else:
        await message.answer("❌ Неверная роль. Выберите 'Староста' или 'Куратор'.")
        return
        
    await state.update_data(role=role, role_text=role_text)
    await message.answer("✍️ Введите ваше ФИО полностью:")
    await state.set_state(Registration.full_name)

@router.message(Registration.full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    if len(full_name) < 5:
        await message.answer("❌ ФИО должно содержать не менее 5 символов. Введите снова:")
        return
        
    await state.update_data(full_name=full_name)
    await message.answer("📞 Введите ваш номер телефона:")
    await state.set_state(Registration.phone)

@router.message(Registration.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    # Простая валидация телефона
    if not re.match(r'^[\d\s\-\+\(\)]+$', phone) or len(phone) < 5:
        await message.answer("❌ Неверный формат телефона. Введите снова:")
        return
        
    await state.update_data(phone=phone)
    await message.answer("🔗 Введите ваш Telegram username (без @):")
    await state.set_state(Registration.telegram)

@router.message(Registration.telegram)
async def process_telegram(message: types.Message, state: FSMContext):
    telegram = message.text.strip().lstrip('@')
    if not telegram:
        await message.answer("❌ Username не может быть пустым. Введите снова:")
        return
        
    await state.update_data(telegram=telegram)
    data = await state.get_data()
    role = data['role']
    
    if role == 'headman':
        await message.answer("🏷️ Введите вашу группу:")
    elif role == 'curator':
        await message.answer("🏷️ Введите группы, которыми вы руководите (через запятую):")
        
    await state.set_state(Registration.groups)

@router.message(Registration.groups)
async def process_groups(message: types.Message, state: FSMContext):
    data = await state.get_data()
    role = data['role']
    now = datetime.datetime.now()
    name = data['full_name']
    email = ''.join(c for c in name.lower() if c.isalnum()) + '@college.edu'
    password = 'temp123'
    phone = data['phone']
    telegram = data['telegram']
    telegram_id = message.from_user.id
    
    try:
        if role == 'headman':
            headman_group = message.text.strip().upper()
            if not headman_group:
                await message.answer("❌ Группа не может быть пустой. Введите снова:")
                return

            cursor.execute('''
            INSERT INTO users (created_at, updated_at, name, email, password, role, phone, telegram, headman_group, telegram_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            ''', (now, now, name, email, password, role, phone, telegram, headman_group, telegram_id))
            conn.commit()

            await message.answer(
                "✅ Регистрация завершена!\n\n"
                "⏳ Ожидайте подтверждения от куратора вашей группы."
            )
            
        elif role == 'curator':
            groups = [g.strip().upper() for g in message.text.split(',') if g.strip()]
            if not groups:
                await message.answer("❌ Необходимо указать хотя бы одну группу. Введите снова:")
                return

            # Кураторы теперь автоматически подтверждаются
            cursor.execute('''
            INSERT INTO users (created_at, updated_at, name, email, password, role, phone, telegram, telegram_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed')
            ''', (now, now, name, email, password, role, phone, telegram, telegram_id))
            conn.commit()

            # Получаем ID нового куратора
            cursor.execute("SELECT last_insert_rowid()")
            curator_id = cursor.fetchone()[0]
            
            for group in groups:
                cursor.execute('''
                INSERT INTO groupfromcurs (created_at, updated_at, name, "group")
                VALUES (?, ?, ?, ?)
                ''', (now, now, name, group))
            conn.commit()
            
            await message.answer(
                "✅ Регистрация завершена!\n\n"
                "🎉 Вы автоматически подтверждены как куратор!\n"
                "Теперь вы можете:\n"
                "• Добавлять студентов\n"
                "• Подтверждать старост\n"
                "• Добавлять пропуски\n"
                "• Смотреть статистику\n"
                "• Экспортировать данные"
            )
            
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при регистрации: {str(e)}")
        await state.clear()