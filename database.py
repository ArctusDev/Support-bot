import asyncpg
import asyncio
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
DB_URL = os.getenv("DB_URL")

async def init_db():
    return await asyncpg.connect(DB_URL)

## Функция для проверки подключения
# async def test_db():
#     try:
#         conn = await asyncpg.connect(DB_URL)
#         print('Подключено')
#         await conn.close()
#     except Exception as e:
#         print('Ошибка подключения: {e}')
#
#
async def create_tables():
    conn = await asyncpg.connect(DB_URL)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                state TEXT,
                category TEXT DEFAULT NULL,
                role TEXT DEFAULT 'user'
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id SERIAL PRIMARY KEY,
                category TEXT DEFAULT NULL,
                user_id BIGINT REFERENCES users(user_id),
                text TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT NOW(),
                operator_id BIGINT DEFAULT NULL
            );
        """)

        print('Таблицы успешно созданы!')
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
    finally:
        await conn.close()
# Запускаем создание таблиц при старте
async def init():
    await create_tables()


async def user_in_db(user_id: int):
    conn = await init_db()
    # Проверяем, есть ли пользователь в таблице. Если нет - добавляем
    user_exists = await conn.fetchval("SELECT 1 FROM users WHERE user_id = $1", user_id)
    if not user_exists:
        print("Пользователя нет в таблице")
        await conn.execute("INSERT INTO users (user_id, state, role) VALUES ($1, $2, $3)", user_id, 'idle', 'USER')
    await conn.close()

# Создаём новую заявку
async def create_ticket(user_id: int, text: str, category: str):
    print(f"Попытка записать заявку: {user_id}, {text}, {category}")
    conn = await init_db()
    try:
        if not category:
            category = "unknown"   # На всякий случай

        ticket_id = await conn.fetchval(
            "INSERT INTO tickets (user_id, text, category) VALUES ($1, $2, $3) RETURNING ticket_id",
            user_id, text, category
        )
        print("Заявка записана")
        return ticket_id
    except Exception as e:
        logger.error(f"Ошибка записи заявки: {e}")
        print(f"Ошибка SQL: {e}")
    finally:
        await conn.close()           # Возвращает id заявки


# Записываем состояние пользователя в БД
async def set_user_state(user_id: int, state: str):
    conn = await init_db()
    try:
        await user_in_db(user_id)
        print("Устанавливаем состояние пользователя")
        await conn.execute(
            "UPDATE users SET state = $1 WHERE user_id = $2",
            state, user_id
        )
        print(f"Установлено состояние пользователя {user_id} : {state}")
    except Exception as e:
        logger.error(f"Ошибка при обновлении состояния пользователя {user_id}: {e}")
    finally:
        await conn.close()

# Получаем состояние пользователя
async def get_user_state(user_id: int):
    conn = await init_db()
    try:
        state = await conn.fetchval("SELECT state FROM users WHERE user_id = $1", user_id)
        return state
    except Exception as e:
        logger.error(f"Ошибка при получении состояния пользователя {user_id}: {e}")
        print(f"ошибка при установке состояния {e}")
        return None
    finally:
        await conn.close()

# Очищаем состояние пользователя
async def clear_user_state(user_id: int):
    conn = await init_db()
    try:
        await conn.execute("UPDATE users SET category = NULL WHERE user_id = $1",
                           user_id)
        print(f"✅ Состояние пользователя {user_id} изменено на 'NULL'.")
    except Exception as e:
        logger.error(f"Ошибка при очистке состояния пользователя {user_id}: {e}")
    finally:
        await conn.close()

async def is_operator(user_id):
    conn = await init_db()
    try:
        check_res = await conn.fetch("SELECT user_id FROM users WHERE role = 'operator' and user_id = $1", user_id)
        if check_res:
            return True
    finally:
        await conn.close()
    return False


# Сохраняем выбранную категорию в БД
async def set_user_category(user_id: int, category: str):
    conn = await init_db()
    try:
        print(f"Устанавливаем категорию {category} для пользователя {user_id}")
        await conn.execute("UPDATE users SET category = $1 WHERE user_id = $2", category, user_id)

    except Exception as e:
        logger.error(f"Ошибка при сохранении категории для {user_id}: {e}")
    finally:
        await conn.close()

# Получаем категорию пользователя
async def get_user_category(user_id: int):
    conn = await init_db()
    try:
        category = await conn.fetchval("SELECT category FROM users WHERE user_id = $1", user_id)
        return category
    except Exception as e:
        logger.error(f"Ошибка при получении категории пользователя {user_id}: {e}")
        return None
    finally:
        await conn.close()


# Получаем список тикетов пользователя
async def get_user_tickets(user_id: int):
    conn = await init_db()
    try:
        rows = await conn.fetch("SELECT ticket_id, category, text, created_at FROM tickets WHERE user_id = $1 and status = 'open' ORDER BY created_at DESC", user_id)
        print(f"{rows}")
        return rows  # Возвращаем список тикетов
    except Exception as e:
        logger.error(f"Ошибка при получении тикетов пользователя {user_id}: {e}")
        return None
    finally:
        await conn.close()


# Функции для ОПЕРАТОРОВ
async def get_all_tickets():
    conn = await init_db()
    try:
        rows =  await conn.fetch("SELECT * FROM tickets WHERE status = 'open'")
        return rows
    finally:
        await conn.close()

async def get_ticket_by_id(ticket_id: int):
    conn = await init_db()
    try:
        return await conn.fetchrow("SELECT * FROM tickets WHERE ticket_id = $1", ticket_id)
    finally:
        await conn.close()

async def update_ticket_status(ticket_id: int, status: str):
    conn = await init_db()
    try:
        await conn.execute("UPDATE tickets SET status = $1 WHERE ticket_id = $2", status, ticket_id)
    finally:
        await conn.close()

async def get_user_role(user_id: int):
    conn = await init_db()
    try:
        role = await conn.fetchval("SELECT role FROM users WHERE user_id = $1", user_id)
        return role
    finally:
        await conn.close()


async def set_user_role(user_id: int, role: str):
    conn = await init_db()
    try:
        await conn.execute("UPDATE users SET role = $1 WHERE user_id = $2", role, user_id)
        print(f"✅ Роль пользователя {user_id} изменена на {role}")
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении роли пользователя {user_id}: {e}")
    finally:
        await conn.close()

async def find_operator_for_ticket(ticket_id: int):
    conn = await init_db()
    try:
        operator_id = await conn.fetchval("SELECT user_id FROM users WHERE state = $1", f"chating_{ticket_id}")
        return operator_id
    finally:
        await conn.close()

async def add_admin_user(user_id: int, role: str):
    conn = await init_db()
    try:
        await conn.execute("INSERT INTO users (user_id, role) VALUES ($1, $2)", user_id, role)
    finally:
        await conn.close()



asyncio.run(init_db())