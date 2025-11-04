import datetime
from aiogram import types
from aiogram.fsm.context import FSMContext
from db.database import cursor
from fsm.states import ViewStats
from ui.keyboards import get_period_keyboard, get_stats_type_keyboard, get_back_keyboard
from handlers import router

@router.message(lambda message: message.text == '📊 Просмотр статистики')
async def view_stats(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    cursor.execute("SELECT role, status FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    
    if user is None or user[1] != 'confirmed':
        await message.answer("❌ Доступ запрещён.")
        return
        
    await message.answer(
        "📅 Выберите период для статистики:",
        reply_markup=get_period_keyboard()
    )
    await state.set_state(ViewStats.period)

@router.message(ViewStats.period)
async def process_period(message: types.Message, state: FSMContext):
    period = message.text
    if period == '↩️ Назад':
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=types.ReplyKeyboardRemove())
        return
        
    # Определяем даты периода
    today = datetime.date.today()
    if period == 'За сегодня':
        start_date = today.isoformat()
        end_date = today.isoformat()
        period_sql = "date = ?"
        params = [start_date]
    elif period == 'За неделю':
        start_date = (today - datetime.timedelta(days=7)).isoformat()
        end_date = today.isoformat()
        period_sql = "date BETWEEN ? AND ?"
        params = [start_date, end_date]
    elif period == 'За месяц':
        start_date = (today - datetime.timedelta(days=30)).isoformat()
        end_date = today.isoformat()
        period_sql = "date BETWEEN ? AND ?"
        params = [start_date, end_date]
    else:  # За всё время
        period_sql = "1=1"
        params = []
    
    await state.update_data(period_sql=period_sql, params=params, period_display=period)
    
    await message.answer(
        "📈 Выберите тип статистики:",
        reply_markup=get_stats_type_keyboard()
    )
    await state.set_state(ViewStats.type)

@router.message(ViewStats.type)
async def process_stats_type(message: types.Message, state: FSMContext):
    stat_type = message.text
    if stat_type == '↩️ Назад':
        await state.set_state(ViewStats.period)
        await message.answer("📅 Выберите период:", reply_markup=get_period_keyboard())
        return
        
    data = await state.get_data()
    period_sql = data['period_sql']
    params = data['params']
    period_display = data['period_display']
    
    telegram_id = message.from_user.id
    cursor.execute("SELECT name, role, headman_group FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    
    response = f"📊 Статистика {stat_type.lower()} ({period_display})\n\n"
    
    try:
        if stat_type == '📊 По студентам':
            # Получаем доступные группы для пользователя
            if user[1] == 'headman':
                groups = [user[2]]
                groups_sql = "AND a.group = ?"
                groups_params = [user[2]]
            elif user[1] == 'curator':
                cursor.execute('SELECT "group" FROM groupfromcurs WHERE name = ?', (user[0],))
                groups = [row[0] for row in cursor.fetchall()]
                if groups:
                    placeholders = ','.join('?' for _ in groups)
                    groups_sql = f"AND a.group IN ({placeholders})"
                    groups_params = groups
                else:
                    groups_sql = "AND 1=0"
                    groups_params = []
            else:  # admin
                groups_sql = ""
                groups_params = []
            
            # Статистика по студентам
            cursor.execute(f'''
            SELECT 
                a.student_name,
                a.group,
                SUM(a.hours_missed) as total_hours,
                SUM(CASE WHEN a.reason = 'ув' THEN a.hours_missed ELSE 0 END) as excused_hours
            FROM attendances a
            WHERE {period_sql} {groups_sql}
            GROUP BY a.student_name, a.group
            ORDER BY a.group, total_hours DESC
            ''', params + groups_params)
            
            stats = cursor.fetchall()
            
            if not stats:
                response += "❌ Нет данных за выбранный период."
            else:
                current_group = None
                for stat in stats:
                    if stat[1] != current_group:
                        current_group = stat[1]
                        response += f"\n🏷️ Группа: {current_group}\n"
                    
                    total = stat[2] or 0
                    excused = stat[3] or 0
                    unexcused = total - excused
                    
                    response += (
                        f"👤 {stat[0]}\n"
                        f"   • Всего: {total}ч\n"
                        f"   • Уважительных: {excused}ч\n"
                        f"   • Неуважительных: {unexcused}ч\n\n"
                    )
                    
                    # Ограничиваем длину сообщения
                    if len(response) > 3500:
                        response += "... (сообщение обрезано)"
                        break
        
        elif stat_type == '🏷️ По группам':
            # Получаем доступные группы для пользователя
            if user[1] == 'headman':
                groups = [user[2]]
                groups_sql = "AND a.group = ?"
                groups_params = [user[2]]
            elif user[1] == 'curator':
                cursor.execute('SELECT "group" FROM groupfromcurs WHERE name = ?', (user[0],))
                groups = [row[0] for row in cursor.fetchall()]
                if groups:
                    placeholders = ','.join('?' for _ in groups)
                    groups_sql = f"AND a.group IN ({placeholders})"
                    groups_params = groups
                else:
                    groups_sql = "AND 1=0"
                    groups_params = []
            else:  # admin
                groups_sql = ""
                groups_params = []
            
            # Статистика по группам
            cursor.execute(f'''
            SELECT 
                a.group,
                COUNT(DISTINCT a.student_name) as student_count,
                SUM(a.hours_missed) as total_hours,
                SUM(CASE WHEN a.reason = 'ув' THEN a.hours_missed ELSE 0 END) as excused_hours,
                ROUND(AVG(a.hours_missed), 1) as avg_per_student
            FROM attendances a
            WHERE {period_sql} {groups_sql}
            GROUP BY a.group
            ORDER BY total_hours DESC
            ''', params + groups_params)
            
            stats = cursor.fetchall()
            
            if not stats:
                response += "❌ Нет данных за выбранный период."
            else:
                for stat in stats:
                    total = stat[2] or 0
                    excused = stat[3] or 0
                    unexcused = total - excused
                    avg_per_student = stat[4] or 0
                    
                    response += (
                        f"🏷️ Группа: {stat[0]}\n"
                        f"👥 Студентов: {stat[1]}\n"
                        f"⏰ Всего пропусков: {total}ч\n"
                        f"✅ Уважительных: {excused}ч\n"
                        f"❌ Неуважительных: {unexcused}ч\n"
                        f"📈 В среднем на студента: {avg_per_student}ч\n\n"
                    )
        
        elif stat_type == '👨‍🏫 По кураторам':
            # Статистика по кураторам
            cursor.execute(f'''
            SELECT 
                g.name as curator_name,
                COUNT(DISTINCT a.group) as group_count,
                COUNT(DISTINCT a.student_name) as student_count,
                SUM(a.hours_missed) as total_hours,
                SUM(CASE WHEN a.reason = 'ув' THEN a.hours_missed ELSE 0 END) as excused_hours,
                ROUND(AVG(a.hours_missed), 1) as avg_per_student
            FROM attendances a
            JOIN groupfromcurs g ON a.group = g.group
            WHERE {period_sql}
            GROUP BY g.name
            ORDER BY total_hours DESC
            ''', params)
            
            stats = cursor.fetchall()
            
            if not stats:
                response += "❌ Нет данных за выбранный период."
            else:
                for stat in stats:
                    total = stat[3] or 0
                    excused = stat[4] or 0
                    unexcused = total - excused
                    avg_per_student = stat[5] or 0
                    
                    response += (
                        f"👨‍🏫 Куратор: {stat[0]}\n"
                        f"🏷️ Групп: {stat[1]}\n"
                        f"👥 Студентов: {stat[2]}\n"
                        f"⏰ Всего пропусков: {total}ч\n"
                        f"✅ Уважительных: {excused}ч\n"
                        f"❌ Неуважительных: {unexcused}ч\n"
                        f"📈 В среднем на студента: {avg_per_student}ч\n\n"
                    )
        
        elif stat_type == '🏛️ По ЦМК':
            # Статистика по ЦМК (укрупненная по направлениям)
            cursor.execute(f'''
            SELECT 
                SUBSTR(a.group, 1, 3) as direction,
                COUNT(DISTINCT a.group) as group_count,
                COUNT(DISTINCT a.student_name) as student_count,
                SUM(a.hours_missed) as total_hours,
                SUM(CASE WHEN a.reason = 'ув' THEN a.hours_missed ELSE 0 END) as excused_hours,
                ROUND(AVG(a.hours_missed), 1) as avg_per_student
            FROM attendances a
            WHERE {period_sql}
            GROUP BY direction
            ORDER BY total_hours DESC
            ''', params)
            
            stats = cursor.fetchall()
            
            if not stats:
                response += "❌ Нет данных за выбранный период."
            else:
                for stat in stats:
                    total = stat[3] or 0
                    excused = stat[4] or 0
                    unexcused = total - excused
                    avg_per_student = stat[5] or 0
                    
                    response += (
                        f"🏛️ Направление: {stat[0]}\n"
                        f"🏷️ Групп: {stat[1]}\n"
                        f"👥 Студентов: {stat[2]}\n"
                        f"⏰ Всего пропусков: {total}ч\n"
                        f"✅ Уважительных: {excused}ч\n"
                        f"❌ Неуважительных: {unexcused}ч\n"
                        f"📈 В среднем на студента: {avg_per_student}ч\n\n"
                    )
        
        else:
            response = "❌ Неизвестный тип статистики."
            
    except Exception as e:
        response = f"❌ Ошибка при получении статистики: {e}"
    
    # Разбиваем длинные сообщения
    if len(response) > 4000:
        parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(response)
    
    await state.clear()