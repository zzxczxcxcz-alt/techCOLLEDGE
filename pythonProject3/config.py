from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

API_TOKEN = '8330516134:AAGvlwdnN2QG2EoqmtHV3KjqnPanepKzHt8'

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)