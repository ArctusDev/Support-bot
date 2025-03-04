import asyncio
import os
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup,
                           KeyboardButton)
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
import logging
from dotenv import load_dotenv
from setuptools.command.build_ext import use_stubs

from admin import admin_router
from admin import admin_keyboard
from anty_ddos import WriteLimit
from database import (
    init, set_user_state, get_user_state, clear_user_state, set_user_category, get_user_category,
    create_ticket, get_user_tickets, is_operator
)
from chat import chat_router

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_URL = os.getenv("CHANNEL_URL")

logging.basicConfig(level=logging.INFO, filename="bot_errors.log", filemode="a",
                    format="%(asctime)s - %(levelname)s - %(message)s", encoding='utf-8')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

VALID_CATEGORIES = {"error", "suggestion", "question"}

# Проверка подписки на канал
async def is_user_subscribed(user_id: int) -> bool:
    try:
        chat_member = await bot.get_chat_member(CHANNEL_ID, user_id)
        print(CHANNEL_ID)
        print(chat_member)
        return chat_member.status in ["member", "administrator", "creator"]
    except TelegramBadRequest:
        print('FALSE')
        return False

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📩 Создать заявку")],
            [KeyboardButton(text="ℹ️ Помощь"), KeyboardButton(text="📜 Мои заявки")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

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

    if not await is_user_subscribed(user_id):
        await message.answer(
            "🔔 Для использования бота вам нужно подписаться на канал:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Перейти в канал", url=f"https://t.me/{CHANNEL_URL}")],
                [InlineKeyboardButton(text="✅ Я подписался!", callback_data="check_subscription")]
            ])
        )
        return  # Не даём пользоваться ботом, пока не подпишется)

    if await is_operator(user_id):
        await message.answer("👋 Привет, оператор! Выберите действие:", reply_markup=admin_keyboard())
    else:
        await message.answer("👋 Привет! Выберите действие:", reply_markup=main_menu())

@router.callback_query(lambda c: c.data == "check_subscription")
async def check_subscription(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if await is_user_subscribed(user_id):
        await callback_query.message.edit_text("✅ Подписка подтверждена!")
        await start_command(callback_query.message)    # Перезапуск start
    else:
        await callback_query.answer("❌ Вы ещё не подписаны!", show_alert=True)


@router.callback_query(lambda c: c.data == "cancel_ticket")
async def cancel_ticket(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    await clear_user_state(user_id)
    await callback_query.message.edit_text("❌ Вы отменили создание заявки.")
    await callback_query.answer()

@router.message(lambda message: message.text == "ℹ️ Помощь")
async def help_command(message: types.Message):
    user_id = message.from_user.id
    state = await get_user_state(user_id)
    print(state)
    if state.startswith("chating_"):
        await message.answer("⚠️Вы находитесь в чате с оператором")
        return
    await message.answer("ℹ️ Как создать заявку?\n\n"
                         "1️⃣ Нажмите '📩 Создать заявку'\n"
                         "2️⃣ Выберите категорию\n"
                         "3️⃣ Опишите проблему\n"
                         "4️⃣ Дождитесь ответа оператора.", reply_markup=main_menu())

@router.message(lambda message: message.text == "📩 Создать заявку")
async def create_ticket_button(message: types.Message):
    user_id = message.from_user.id
    state = await get_user_state(user_id)
    print(state)
    if state.startswith("chating_"):
        await message.answer("⚠️Вы находитесь в чате с оператором")
        return
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
    if message.text:
        text = message.text.strip()
    elif message.caption:
        text = message.caption.strip()
    else:
        text = ""

    print(text)

    if text == '📜 Мои заявки' or text == '📩 Создать заявку' or text == 'ℹ️ Помощь':
        await message.answer("❌ Ошибка при создании тикета")
        await set_user_state(user_id, state='idle')
        return
    if message.animation:
        await message.answer("❌ Ошибка при создании тикета, нельзя отправлять анимации")
        await set_user_state(user_id, state='idle')
        return
    if message.audio:
        await message.answer("❌ Ошибка при создании тикета, нельзя отправлять аудио")
        await set_user_state(user_id, state='idle')
        return

    # Если группа файлов (фото + видео)
    if message.media_group_id:
        await message.answer("❌ Ошибка. Пожалуйста, присылайте по одному файлу с описанием проблемы.")
        await set_user_state(user_id, state='idle')
        return
    # Если там фото, видео или документ
    if text and message.photo:
        file_id = message.photo[-1].file_id
        file_info = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        text += f". Фото: {file_url}"
    elif text and message.video:
        file_id = message.video.file_id
        file_info = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        text += f". Видео: {file_url}"
    elif text and message.document:
        file_id = message.document.file_id
        file_info = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        text += f". Документ: {file_url}"
    elif message.document:
        file_id = message.document.file_id
        file_info = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        text = f"Документ: {file_url}"
    elif message.video:
        file_id = message.video.file_id
        file_info = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        text = f"Видео-заявка: {file_url}"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_info = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        text = f"Фото-заявка: {file_url}"

    if not text:
        await message.answer("❌ Создана пустая заявка или недопустимый формат файлов.")
        return
    category = await get_user_category(user_id) or "unknown"
    try:
        ticket_id = await create_ticket(user_id, text, category)
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
        await message.answer("📜 У вас пока нет заявок.", reply_markup=main_menu())
        return
    response = "📜 Ваши заявки:\n\n"
    for ticket in tickets[:]:
        response += f"🔹 #{ticket['ticket_id']} ({ticket['category']}): {ticket['text'][:100]} {ticket['created_at']}\n"
    await message.answer(response)


async def main():
    await init()
    router.message.middleware(WriteLimit(limit=3.0))

    dp.include_router(router)
    dp.include_router(admin_router)
    dp.include_router(chat_router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
