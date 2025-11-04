import datetime
import pandas as pd
from io import BytesIO
from aiogram import types
from aiogram.fsm.context import FSMContext
from db.database import cursor
from fsm.states import ExportStats
from ui.keyboards import get_period_keyboard, get_back_keyboard
from handlers import router

@router.message(lambda message: message.text == '📤 Экспорт в Excel')
async def export_excel(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    cursor.execute("SELECT role, status FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    
    if user is None or user[1] != 'confirmed':
        await message.answer("❌ Доступ запрещён.")
        return
        
    await message.answer(
        "📅 Выберите период для экспорта:",
        reply_markup=get_period_keyboard()
    )
    await state.set_state(ExportStats.period)

@router.message(ExportStats.period)
async def process_export_period(message: types.Message, state: FSMContext):
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
        filename_suffix = f"_{today}"
    elif period == 'За неделю':
        start_date = (today - datetime.timedelta(days=7)).isoformat()
        end_date = today.isoformat()
        period_sql = "date BETWEEN ? AND ?"
        params = [start_date, end_date]
        filename_suffix = f"_{start_date}_to_{end_date}"
    elif period == 'За месяц':
        start_date = (today - datetime.timedelta(days=30)).isoformat()
        end_date = today.isoformat()
        period_sql = "date BETWEEN ? AND ?"
        params = [start_date, end_date]
        filename_suffix = f"_{start_date}_to_{end_date}"
    else:  # За всё время
        period_sql = "1=1"
        params = []
        filename_suffix = "_all_time"
    
    await message.answer("⏳ Формируем Excel файл...")
    
    try:
        # Получаем данные для экспорта
        cursor.execute(f'''
        SELECT 
            a.student_name as "Студент",
            a.group as "Группа",
            a.date as "Дата",
            a.hours_missed as "Пропущено часов",
            CASE 
                WHEN a.reason = 'ув' THEN 'Уважительная'
                ELSE 'Неуважительная'
            END as "Причина",
            a.description as "Описание",
            a.subject as "Предмет",
            u.name as "Добавил"
        FROM attendances a
        LEFT JOIN users u ON a.created_by = u.id
        WHERE {period_sql}
        ORDER BY a.group, a.student_name, a.date
        ''', params)
        
        attendance_data = cursor.fetchall()
        
        # Создаем DataFrame с пропусками
        df_attendance = pd.DataFrame(attendance_data, columns=[
            'Студент', 'Группа', 'Дата', 'Пропущено часов', 
            'Причина', 'Описание', 'Предмет', 'Добавил'
        ])
        
        # Создаем сводную статистику по группам
        cursor.execute(f'''
        SELECT 
            a.group as "Группа",
            COUNT(DISTINCT a.student_name) as "Количество студентов",
            SUM(a.hours_missed) as "Всего пропусков",
            SUM(CASE WHEN a.reason = 'ув' THEN a.hours_missed ELSE 0 END) as "Уважительные",
            SUM(CASE WHEN a.reason = 'неув' THEN a.hours_missed ELSE 0 END) as "Неуважительные",
            ROUND(AVG(a.hours_missed), 1) as "Среднее на студента"
        FROM attendances a
        WHERE {period_sql}
        GROUP BY a.group
        ORDER BY a.group
        ''', params)
        
        group_stats = cursor.fetchall()
        df_groups = pd.DataFrame(group_stats, columns=[
            'Группа', 'Количество студентов', 'Всего пропусков', 
            'Уважительные', 'Неуважительные', 'Среднее на студента'
        ])
        
        # Создаем статистику по студентам
        cursor.execute(f'''
        SELECT 
            a.student_name as "Студент",
            a.group as "Группа",
            SUM(a.hours_missed) as "Всего пропусков",
            SUM(CASE WHEN a.reason = 'ув' THEN a.hours_missed ELSE 0 END) as "Уважительные",
            SUM(CASE WHEN a.reason = 'неув' THEN a.hours_missed ELSE 0 END) as "Неуважительные",
            COUNT(*) as "Количество записей"
        FROM attendances a
        WHERE {period_sql}
        GROUP BY a.student_name, a.group
        ORDER BY a.group, "Всего пропусков" DESC
        ''', params)
        
        student_stats = cursor.fetchall()
        df_students = pd.DataFrame(student_stats, columns=[
            'Студент', 'Группа', 'Всего пропусков', 
            'Уважительные', 'Неуважительные', 'Количество записей'
        ])
        
        # Создаем Excel файл в памяти
        bio = BytesIO()
        
        with pd.ExcelWriter(bio, engine='openpyxl') as writer:
            # Лист с детальными пропусками
            df_attendance.to_excel(writer, sheet_name='Пропуски', index=False)
            
            # Лист со статистикой по группам
            df_groups.to_excel(writer, sheet_name='Статистика по группам', index=False)
            
            # Лист со статистикой по студентам
            df_students.to_excel(writer, sheet_name='Статистика по студентам', index=False)
            
            # Настраиваем ширину колонок
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        bio.seek(0)
        
        # Отправляем файл
        filename = f"attendance_report{filename_suffix}.xlsx"
        
        await message.answer_document(
            types.BufferedInputFile(bio.read(), filename=filename),
            caption=f"📊 Отчёт о пропусках ({period.lower()})\n\n"
                   f"• Детальные пропуски\n"
                   f"• Статистика по группам\n"
                   f"• Статистика по студентам\n\n"
                   f"📅 Период: {period}\n"
                   f"📋 Всего записей: {len(df_attendance)}"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при экспорте: {str(e)}")
    
    await state.clear()