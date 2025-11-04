from aiogram import Router

router = Router()

# Импортируем все обработчики
from . import start
from . import registration
from . import confirmation
from . import students
from . import absences
from . import stats
from . import export