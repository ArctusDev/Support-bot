import asyncpg
import asyncio
import os
import logging
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DB_URL")

# Логирование
logging.basicConfig(level=logging.ERROR, filename="bot_errors.log", filemode="a",
                    format="%(asctime)s - %(levelname)s - %(message)s")

async def init_db():
    return await asyncpg.connect(DB_URL)

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
                role TEXT DEFAULT 'user'
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                text TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_states (
                user_id BIGINT PRIMARY KEY,
                state TEXT
            );
        """)

        print('Таблицы успешно созданы!')
    except Exception as e:
        logging.error(f"Ошибка при создании таблиц: {e}")
    finally:
        await conn.close()
# Запускаем создание таблиц при старте
async def init():
    await create_tables()


# Добавляем пользователя, если его нет
async def add_user(user_id: int, role: str = 'user'):
    conn = await init_db()
    await conn.execute(
        "INSERT INTO users (user_id, role) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
        user_id, role
    )
    await conn.close()

# Создаём новую заявку
async def create_ticket(user_id: int, text: str, category: str):
    conn = await init_db()
    ticket_id = await conn.fetchval(
        "INSERT INTO tickets (user_id, text, category) VALUES ($1, $2, $3) RETURNING ticket_id",
        user_id, text, category
    )
    await conn.close()
    return ticket_id            # Возвращает id заявки

# Получаем список открытых заявок
async def get_open_tickets():
    conn = await init_db()
    tickets = await conn.fetch(
        "SELECT * FROM tickets WHERE status = 'open'"
    )
    await conn.close()
    return tickets


async def update_ticket_status(ticket_id: int, status: str):
    conn = await init_db()
    await conn.execute(
        "UPDATE tickets SET status = $1 WHERE ticket_id = $2",
        status, ticket_id
    )
    await conn.close()


# Записываем состояние пользователя в БД
async def set_user_state(user_id: int, state: str):
    conn = await init_db()
    try:
        await conn.execute(
            "INSERT INTO user_states (user_id, state) VALUES ($1, $2) "
            "ON CONFLICT (user_id) DO UPDATE SET state = $2",
            user_id, state
        )
    except Exception as e:
        logging.error(f"Ошибка при обновлении состояния пользователя {user_id}: {e}")
    finally:
        await conn.close()

# Получаем состояние пользователя
async def get_user_state(user_id: int):
    conn = await init_db()
    try:
        state = await conn.fetchval("SELECT state FROM user_states WHERE user_id = $1", user_id)
        return state
    except Exception as e:
        logging.error(f"Ошибка при получении состояния пользователя {user_id}: {e}")
        return None
    finally:
        await conn.close()

# Очищаем состояние пользователя
async def clear_user_state(user_id: int):
    conn = await init_db()
    try:
        await conn.execute("DELETE FROM user_states WHERE user_id = $1", user_id)
    except Exception as e:
        logging.error(f"Ошибка при очистке состояния пользователя {user_id}: {e}")
    finally:
        await conn.close()


# Сохраняем выбранную категорию в БД
async def set_user_category(user_id: int, category: str):
    conn = await init_db()
    try:
        await conn.execute(
            "INSERT INTO user_states (user_id, state, category) VALUES ($1, 'writing_text', $2) "
            "ON CONFLICT (user_id) DO UPDATE SET category = $2",
            user_id, category
        )
    except Exception as e:
        logging.error(f"Ошибка при сохранении категории для {user_id}: {e}")
    finally:
        await conn.close()

# Получаем категорию пользователя
async def get_user_category(user_id: int):
    conn = await init_db()
    try:
        category = await conn.fetchval("SELECT category FROM user_states WHERE user_id = $1", user_id)
        return category
    except Exception as e:
        logging.error(f"Ошибка при получении категории пользователя {user_id}: {e}")
        return None
    finally:
        await conn.close()


# Получаем список тикетов пользователя
async def get_user_tickets(user_id: int):
    conn = await init_db()
    try:
        rows = await conn.fetch("SELECT id, category, text, created_at FROM tickets WHERE user_id = $1 ORDER BY created_at DESC", user_id)
        return rows  # Возвращаем список тикетов
    except Exception as e:
        logging.error(f"Ошибка при получении тикетов пользователя {user_id}: {e}")
        return None
    finally:
        await conn.close()

asyncio.run(init_db())