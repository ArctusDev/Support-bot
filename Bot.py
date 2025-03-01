import asyncio
import os
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import logging
from dotenv import load_dotenv
from admin import router as admin_router
from admin import admin_keyboard
from database import (
    init, set_user_state, get_user_state, clear_user_state, set_user_category, get_user_category,
    create_ticket, get_user_tickets, get_operators, is_operator, get_ticket_by_id
)
from chat import chat_router

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO, filename="bot_errors.log", filemode="a",
                    format="%(asctime)s - %(levelname)s - %(message)s", encoding='utf-8')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

VALID_CATEGORIES = {"error", "suggestion", "question"}

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📩 Создать заявку")],
            [KeyboardButton(text="ℹ️ Помощь"), KeyboardButton(text="📜 Мои заявки")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

# @router.message()
# async def debug_handler(message: types.Message):
#     print(f"🔍 bot.py Бот получил сообщение: {message.text} от {message.from_user.id}")

def category_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Ошибка", callback_data="category_error")],
        [InlineKeyboardButton(text="💡 Улучшение", callback_data="category_suggestion")],
        [InlineKeyboardButton(text="❓ Вопрос", callback_data="category_question")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_ticket")]
    ])

@router.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    if await is_operator(user_id):
        await message.answer("👋 Привет, оператор! Выберите действие:", reply_markup=admin_keyboard())
    else:
        await message.answer("👋 Привет! Выберите действие:", reply_markup=main_menu())

@router.callback_query(lambda c: c.data == "cancel_ticket")
async def cancel_ticket(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    await clear_user_state(user_id)
    await callback_query.message.edit_text("❌ Вы отменили создание заявки.")
    await callback_query.answer()

@router.message(lambda message: message.text == "ℹ️ Помощь")
async def help_command(message: types.Message):
    await message.answer("ℹ️ Как создать заявку?\n\n"
                         "1️⃣ Нажмите '📩 Создать заявку'\n"
                         "2️⃣ Выберите категорию\n"
                         "3️⃣ Опишите проблему\n"
                         "4️⃣ Дождитесь ответа оператора.")

@router.message(lambda message: message.text == "📩 Создать заявку")
async def create_ticket_button(message: types.Message):
    if await is_operator(message.from_user.id):
        await message.answer("Вы оператор, вы не можете создавать заявки.")
    else:
        await message.answer("Выберите тип обращения:", reply_markup=category_keyboard())
        await set_user_state(message.from_user.id, "choosing_category")

@router.callback_query(lambda c: c.data.startswith("category_"))
async def receive_category(callback_query: CallbackQuery):
    category = callback_query.data.split("_")[1]
    if category not in VALID_CATEGORIES:
        await callback_query.answer("❌ Ошибка! Неверная категория.")
        return
    await set_user_category(callback_query.from_user.id, category)
    await set_user_state(callback_query.from_user.id, "writing_text")
    await callback_query.message.answer("Теперь опишите вашу проблему:")
    await callback_query.answer()

@router.message(lambda message: asyncio.run(get_user_state(message.from_user.id)) == "writing_text")
async def save_ticket(message: types.Message):
    user_id = message.from_user.id
    category = await get_user_category(user_id) or "unknown"
    try:
        ticket_id = await create_ticket(user_id, message.text, category)
        await message.answer(f"✅ Ваша заявка #{ticket_id} принята!")
        await set_user_state(user_id, state='open')
        await clear_user_state(user_id)
    except Exception as e:
        logging.exception(f"Ошибка при создании тикета: {e}")
        await message.answer("❌ Ошибка при создании тикета. Попробуйте позже.")

@router.message(lambda message: message.text == "📜 Мои заявки")
async def my_tickets(message: types.Message):
    user_id = message.from_user.id
    tickets = await get_user_tickets(user_id)
    if not tickets:
        await message.answer("📜 У вас пока нет заявок.")
        return
    response = "📜 Ваши заявки:\n\n"
    for ticket in tickets[:]:
        response += f"🔹 #{ticket['ticket_id']} ({ticket['category']}): {ticket['text'][:100]} {ticket['created_at']}\n"
    await message.answer(response)

# @router.message()
# async def fallback_handler(message: types.Message):
#     user_id = message.from_user.id
#     if await is_operator(user_id):
#         return
#     await message.answer("❌ Я вас не понял. Используйте кнопки в меню.", reply_markup=main_menu())

async def main():
    await init()
    dp.include_router(admin_router)
    dp.include_router(router)
    dp.include_router(chat_router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
