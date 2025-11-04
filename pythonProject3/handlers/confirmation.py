import datetime
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db.database import cursor, conn
from ui.keyboards import get_main_keyboard
from handlers import router

# Подтверждение старост куратором
@router.message(lambda message: message.text == '✅ Подтвердить старосту')
async def confirm_headman(message: types.Message):
    telegram_id = message.from_user.id
    cursor.execute("SELECT id, name, role, status FROM users WHERE telegram_id = ?", (telegram_id,))
    current = cursor.fetchone()
    
    if current is None or current[2] != 'curator' or current[3] != 'confirmed':
        await message.answer("❌ Доступ запрещён. Только подтверждённые кураторы могут подтверждать старост.")
        return
        
    curator_name = current[1]
    cursor.execute('SELECT "group" FROM groupfromcurs WHERE name = ?', (curator_name,))
    groups = [row[0] for row in cursor.fetchall()]
    
    if not groups:
        await message.answer("❌ У вас нет назначенных групп.")
        return
        
    cursor.execute("SELECT * FROM users WHERE role = 'headman' AND status = 'pending'")
    pending = cursor.fetchall()
    filtered_pending = [p for p in pending if p[11] in groups]  # headman_group
    
    if not filtered_pending:
        await message.answer("✅ Нет ожидающих подтверждения старост в ваших группах.")
        return
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for user in filtered_pending:
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(
                text=f"{user[4]} - {user[11]}", 
                callback_data=f"confirm_headman_{user[0]}"
            )]
        )
        
    await message.answer("👥 Выберите старосту для подтверждения:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data and c.data.startswith('confirm_headman_'))
async def process_confirm_headman(callback: types.CallbackQuery):
    user_id = int(callback.data.split('_')[2])
    now = datetime.datetime.now()
    
    cursor.execute("UPDATE users SET status = 'confirmed', updated_at = ? WHERE id = ?", (now, user_id))
    conn.commit()
    
    # Получаем данные подтверждённого пользователя
    cursor.execute("SELECT name, telegram_id FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user and user[1]:
        try:
            await callback.bot.send_message(
                user[1],
                "🎉 Ваш статус старосты подтверждён куратором!\n\n"
                "Теперь вы можете работать с системой учёта посещаемости."
            )
        except:
            pass  # Если бот не может написать пользователю
    
    await callback.message.edit_text(f"✅ Староста {user[0]} подтверждён.")
    await callback.answer()

# Подтверждение кураторов администратором
@router.message(lambda message: message.text == '✅ Подтвердить куратора')
async def confirm_curator(message: types.Message):
    telegram_id = message.from_user.id
    cursor.execute("SELECT role, status FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    
    if user is None or user[0] != 'admin' or user[1] != 'confirmed':
        await message.answer("❌ Доступ запрещён. Только администраторы могут подтверждать кураторов.")
        return
        
    cursor.execute("SELECT * FROM users WHERE role = 'curator' AND status = 'pending'")
    pending = cursor.fetchall()
    
    if not pending:
        await message.answer("✅ Нет ожидающих подтверждения кураторов.")
        return
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for user in pending:
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(
                text=f"{user[4]} - {user[8]}", 
                callback_data=f"confirm_curator_{user[0]}"
            )]
        )
        
    await message.answer("👨‍🏫 Выберите куратора для подтверждения:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data and c.data.startswith('confirm_curator_'))
async def process_confirm_curator(callback: types.CallbackQuery):
    user_id = int(callback.data.split('_')[2])
    now = datetime.datetime.now()
    
    cursor.execute("UPDATE users SET status = 'confirmed', updated_at = ? WHERE id = ?", (now, user_id))
    conn.commit()
    
    # Получаем данные подтверждённого пользователя
    cursor.execute("SELECT name, telegram_id FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user and user[1]:
        try:
            await callback.bot.send_message(
                user[1],
                "🎉 Ваш статус куратора подтверждён администратором!\n\n"
                "Теперь вы можете управлять группами и подтверждать старост."
            )
        except:
            pass
    
    await callback.message.edit_text(f"✅ Куратор {user[0]} подтверждён.")
    await callback.answer()