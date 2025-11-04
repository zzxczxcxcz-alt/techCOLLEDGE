from aiogram import types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from db.database import cursor
from ui.keyboards import get_main_keyboard
from fsm.states import Registration
from handlers import router

@router.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        role = user[7]  # role
        status = user[13]  # status
        if status == 'confirmed':
            await message.answer(
                f"🎉 Добро пожаловать обратно, {user[4]}!\n"
                f"👤 Ваша роль: {role}",
                reply_markup=get_main_keyboard(role)
            )
        else:
            await message.answer("⏳ Ваш статус ожидает подтверждения администратором.")
    else:
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text='👨‍🎓 Староста'), types.KeyboardButton(text='👨‍🏫 Куратор')]
            ],
            resize_keyboard=True
        )
        await message.answer(
            "👋 Добро пожаловать в систему учёта посещаемости!\n\n"
            "📝 Выберите роль для регистрации:",
            reply_markup=keyboard
        )
        await state.set_state(Registration.role)