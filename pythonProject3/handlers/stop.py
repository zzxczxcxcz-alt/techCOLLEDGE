import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_TOKEN
from db.database import init_db
from handlers import router


def get_dispute_keyboard():
    keyboard = InlineKeyboardMarkup()
    dispute_button = InlineKeyboardButton(text="🛑 Оспорить", callback_data="dispute")
    keyboard.add(dispute_button)
    return keyboard

@router.callback_query(lambda c: c.data == "dispute")
async def process_dispute(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.answer("Вы выбрали опцию 'Оспорить'. Пожалуйста, напишите, что вы хотите оспорить.")

