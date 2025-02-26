import asyncio
import os
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from database import create_ticket

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_CHAT = os.getenv("SUPPORT_CHAT")

bot = Bot(token= BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()


# Состояния для выбора категории и ввода текста тикета
class TicketState(StatesGroup):
    choosing_category = State()
    writing_text = State()

# Кнопки для выбора категории
def category_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ошибка", callback_data="category_error"),
         InlineKeyboardButton(text="Улучшение", callback_data="category_suggestion"),
         InlineKeyboardButton(text="Вопрос", callback_data="category_question")]
    ])

# Реализация стартового сообщения - проблема!!!
@router.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать заявку", callback_data="create_ticket")]
    ])
    await message.answer("Привет! Я бот тезподдержки! \n\n"
                         "Нажмите кнопку ниже, чтобы создать заявку.",
                         reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "create_ticket")
async def create_ticket_callback(callback_query: CallbackQuery, state: FSMContext):
    await ask_category(callback_query.message, state)
    await callback_query.answer()


# Обрабатываем команду, спрашиваем категорию
@router.message(Command("new_ticket"))
async def ask_category(message: types.Message, state: FSMContext):
    await message.answer("Выберите тип обращения:", reply_markup=category_keyboard())
    await state.set_state(TicketState.choosing_category)

# Обрабатываем выбор категории
@router.callback_query(lambda c: c.data.startswith("category_"))
async def receive_category(callback_query: CallbackQuery, state: FSMContext):
    category = callback_query.data.split('_')[1]
    await state.update_data(category=category)
    await callback_query.message.answer('Теперь опишите вашу проблему:')
    await state.set_state(TicketState.writing_text)
    await callback_query.answer()


# Принимаем обращение и сохраняем текст тикета в базу
@router.message(TicketState.writing_text)
async def save_ticket(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    category = data.get("category", "unknown") # Если что-то пошло не так

    ticket_id = await create_ticket(user_id, message.text, category)
    await message.answer(f"Ваша заявка #{ticket_id} принята в категорию: {category.capitalize()}!")

    # Отправляем операторам уведомление
    await bot.send_message(SUPPORT_CHAT, f"Новое обращение #{ticket_id}({category}):\n{message.text}")

    await state.clear()

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())