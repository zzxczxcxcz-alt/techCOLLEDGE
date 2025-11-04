from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard(role):
    if role == 'headman':
        keyboard = [
            [KeyboardButton(text='📝 Добавить пропуски')],
            [KeyboardButton(text='📊 Просмотр статистики')],
            [KeyboardButton(text='✏️ Редактировать студентов')]
        ]
    elif role == 'curator':
        keyboard = [
            [KeyboardButton(text='👥 Добавить студентов'), KeyboardButton(text='✅ Подтвердить старосту')],
            [KeyboardButton(text='📝 Добавить пропуски'), KeyboardButton(text='📊 Просмотр статистики')],
            [KeyboardButton(text='✏️ Редактировать студентов'), KeyboardButton(text='📤 Экспорт в Excel')]
        ]
    elif role == 'admin':
        keyboard = [
            [KeyboardButton(text='✅ Подтвердить куратора')],
            [KeyboardButton(text='📊 Просмотр статистики')],
            [KeyboardButton(text='📤 Экспорт в Excel')]
        ]
    else:
        keyboard = []
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_period_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='За сегодня'), KeyboardButton(text='За неделю')],
            [KeyboardButton(text='За месяц'), KeyboardButton(text='За всё время')],
            [KeyboardButton(text='↩️ Назад')]
        ],
        resize_keyboard=True
    )

def get_stats_type_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📊 По студентам'), KeyboardButton(text='🏷️ По группам')],
            [KeyboardButton(text='👨‍🏫 По кураторам'), KeyboardButton(text='🏛️ По ЦМК')],
            [KeyboardButton(text='↩️ Назад')]
        ],
        resize_keyboard=True
    )

def get_edit_students_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='✏️ Изменить студента'), KeyboardButton(text='🗑️ Удалить студента')],
            [KeyboardButton(text='👀 Показать список'), KeyboardButton(text='↩️ Назад')]
        ],
        resize_keyboard=True
    )

def get_back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='↩️ Назад')]],
        resize_keyboard=True
    )