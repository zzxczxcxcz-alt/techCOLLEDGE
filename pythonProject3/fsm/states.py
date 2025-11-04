from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    role = State()
    full_name = State()
    phone = State()
    telegram = State()
    groups = State()

class AddStudents(StatesGroup):
    group = State()
    students_list = State()

class EditStudents(StatesGroup):
    group = State()
    action = State()
    student_name = State()
    new_name = State()

class AddAbsence(StatesGroup):
    student = State()
    hours = State()
    reason = State()
    description = State()

class ViewStats(StatesGroup):
    period = State()
    type = State()

class ExportStats(StatesGroup):
    period = State()