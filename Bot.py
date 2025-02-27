import asyncio
import os
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import logging
from dotenv import load_dotenv
from anty_ddos import RateLimitMiddleware
from database import (
    init,
    set_user_state,
    get_user_state,
    clear_user_state,
    set_user_category,
    get_user_category,
    create_ticket,
    get_user_tickets
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_CHAT = os.getenv("SUPPORT_CHAT")

# Настраиваем логирование
logging.basicConfig(level=logging.ERROR, filename="bot_errors.log", filemode="a",
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Создаём бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# Допустимые категории тикетов
VALID_CATEGORIES = {"error", "suggestion", "question"}

# Главное меню с кнопками внизу экрана
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📩 Создать заявку")],
            [KeyboardButton(text="ℹ️ Помощь"), KeyboardButton(text="📜 Мои заявки")]
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

# Кнопки выбора категории тикета
def category_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Ошибка", callback_data="category_error")],
        [InlineKeyboardButton(text="💡 Улучшение", callback_data="category_suggestion")],
        [InlineKeyboardButton(text="❓ Вопрос", callback_data="category_question")]
    ])

# Обработчик команды /start
@router.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("👋 Привет! Выберите действие:", reply_markup=main_menu())


# Обработчик команды /cancel (отмена заявки)
@router.message(Command("cancel"))
async def cancel_command(message: types.Message):
    await clear_user_state(message.from_user.id)  # Очищаем состояние пользователя
    await message.answer("🚫 Вы отменили создание тикета.", reply_markup=main_menu())

# Обработчик кнопки "ℹ️ Помощь"
@router.message(lambda message: message.text and message.text.strip().startswith("ℹ️ Помощь"))
async def help_command(message: types.Message):
    await message.answer("ℹ️ Как создать заявку?\n\n"
                         "1️⃣ Нажмите '📩 Создать заявку'\n"
                         "2️⃣ Выберите категорию\n"
                         "3️⃣ Опишите проблему\n"
                         "4️⃣ Дождитесь ответа оператора.")

# Обработчик кнопки "📩 Создать заявку"
@router.message(lambda message: message.text and message.text.strip().startswith("📩 Создать заявку"))
async def create_ticket_button(message: types.Message):
    await ask_category(message)

# Обработчик кнопки "📜 Мои заявки"
@router.message(lambda message: message.text and message.text.strip().startswith("📜 Мои заявки"))
async def my_tickets(message: types.Message):
    user_id = message.from_user.id
    tickets = await get_user_tickets(user_id)  # Получаем заявки пользователя из БД

    if not tickets:
        await message.answer("📜 У вас пока нет заявок.")
        return

    response = "📜 Ваши заявки:\n\n"
    for ticket in tickets[:5]:
        response += f"🔹 #{ticket['id']} ({ticket['category']}): {ticket['text'][:50]}...\n"

    await message.answer(response)

# Обработчик команды /new_ticket (создание заявки)
@router.message(Command("new_ticket"))
async def ask_category(message: types.Message):
    await message.answer("Выберите тип обращения:", reply_markup=category_keyboard())
    await set_user_state(message.from_user.id, "choosing_category")

# Обработчик выбора категории
@router.callback_query(lambda c: c.data.startswith("category_"))
async def receive_category(callback_query: CallbackQuery):
    category = callback_query.data.split("_")[1]

    if category not in VALID_CATEGORIES:
        await callback_query.answer("❌ Ошибка! Неверная категория.")
        return
    await set_user_category(callback_query.from_user.id, category)
    await callback_query.message.answer("Теперь опишите вашу проблему:")
    await callback_query.answer()


# Обработчик ввода текста заявки
@router.message()
async def save_ticket(message: types.Message):
    user_id = message.from_user.id
    state = await get_user_state(user_id)  # Получаем состояние пользователя

    if state != "writing_text":
        return

    category = await get_user_category(user_id) or "unknown"

    try:
        ticket_id = await create_ticket(user_id, message.text, category)
        await message.answer(f"✅ Ваша заявка #{ticket_id} принята в категорию: {category.capitalize()}!")

        try:
            await bot.send_message(SUPPORT_CHAT, f"📩 Новый тикет #{ticket_id} ({category}):\n{message.text}")
        except Exception as e:
            logging.error(f"Ошибка отправки в SUPPORT_CHAT ({SUPPORT_CHAT}): {e}")

    except Exception as e:
        logging.error(f"Ошибка при создании тикета: {e}")
        await message.answer("❌ Ошибка при создании тикета. Попробуйте позже.")

    await clear_user_state(user_id)  # Очищаем состояние в БД


# Обработчик неизвестных команд (чтобы бот не зависал)
@router.message()
async def fallback_handler(message: types.Message):
    await message.answer("❓ Я вас не понял. Выберите действие в меню.", reply_markup=main_menu())


async def main():
    await init()
    dp.update.middleware(RateLimitMiddleware(limit=2.0))
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())