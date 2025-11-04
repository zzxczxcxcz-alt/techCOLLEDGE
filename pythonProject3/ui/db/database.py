import sqlite3
import logging

logger = logging.getLogger(__name__)

conn = sqlite3.connect('attendance.db', check_same_thread=False)
cursor = conn.cursor()

def init_db():
    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "users" (
        "id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "created_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
        "updated_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
        "deleted_at" DATETIME NULL,
        "name" TEXT NOT NULL,
        "email" TEXT UNIQUE,
        "password" TEXT,
        "role" TEXT DEFAULT 'student',
        "phone" TEXT,
        "telegram" TEXT,
        "group" TEXT,
        "headman_group" TEXT,
        "telegram_id" INTEGER UNIQUE,
        "status" TEXT DEFAULT 'pending'
    );
    ''')

    # Таблица групп кураторов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "groupfromcurs" (
        "id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "created_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
        "updated_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
        "deleted_at" DATETIME NULL,
        "name" TEXT,
        "group" TEXT
    );
    ''')

    # Таблица пропусков
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "attendances" (
        "id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "created_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
        "updated_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
        "deleted_at" DATETIME NULL,
        "student_name" TEXT NOT NULL,
        "group" TEXT NOT NULL,
        "date" TEXT NOT NULL,
        "hours_missed" INTEGER NOT NULL,
        "reason" TEXT NOT NULL,
        "description" TEXT,
        "created_by" INTEGER,
        "subject" TEXT,
        "status" TEXT
    );
    ''')

    # Индексы
    cursor.execute('CREATE INDEX IF NOT EXISTS "idx_attendances_deleted_at" ON "attendances" ("deleted_at");')
    cursor.execute('CREATE INDEX IF NOT EXISTS "idx_groupfromcurs_deleted_at" ON "groupfromcurs" ("deleted_at");')
    cursor.execute('CREATE INDEX IF NOT EXISTS "idx_users_deleted_at" ON "users" ("deleted_at");')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS "idx_users_email" ON "users" ("email");')
    cursor.execute('CREATE INDEX IF NOT EXISTS "idx_users_group" ON "users" ("group");')
    cursor.execute('CREATE INDEX IF NOT EXISTS "idx_attendances_group" ON "attendances" ("group");')
    cursor.execute('CREATE INDEX IF NOT EXISTS "idx_attendances_student" ON "attendances" ("student_name");')

    conn.commit()
    logger.info("База данных инициализирована")