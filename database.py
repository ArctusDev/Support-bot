import asyncpg
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DB_URL")

# async def test_db():
#     try:
#         conn = await asyncpg.connect(DB_URL)
#         print('Подключено')
#         await conn.close()
#     except Exception as e:
#         print('Ошибка подключения: {e}')
#
#
# async def create_tables():
#     conn = await asyncpg.connect(DB_URL)
#
#     await conn.execute("""
#         CREATE TABLE IF NOT EXISTS users (
#             user_id BIGINT PRIMARY KEY,
#             role TEXT DEFAULT 'user'
#         );
#     """)
#
#     await conn.execute("""
#         CREATE TABLE IF NOT EXISTS tickets (
#             ticket_id SERIAL PRIMARY KEY,
#             user_id BIGINT REFERENCES users(user_id),
#             text TEXT,
#             status TEXT DEFAULT 'open',
#             created_at TIMESTAMP DEFAULT NOW()
#         );
#     """)
#
#     print('Таблицы успешно созданы!')
#     await conn.close()

async def init_db():
    return await asyncpg.connect(DB_URL)

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

asyncio.run(init_db())