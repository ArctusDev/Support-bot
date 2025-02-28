import os
from aiogram import Bot
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from database import get_all_tickets, update_ticket_status, get_ticket_by_id, set_user_role, get_user_role, \
    add_admin_user, set_user_state
from dotenv import load_dotenv
import logging


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")


bot = Bot(token=BOT_TOKEN)
router = Router()

# Клавиатура для операторов
def admin_keyboard():
    keyboard = [
        [KeyboardButton(text="📋 Все заявки")],
        [KeyboardButton(text="👤 Добавить оператора")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)


# Просмотр всех заявок
@router.message(lambda msg: msg.text.find("Все заявки") != -1)
async def view_tickets(message: types.Message):
    user_id = message.from_user.id
    role = await get_user_role(user_id)
    if role != 'operator':
        return

    tickets = await get_all_tickets()
    if not tickets:
        await message.answer("📭 Нет активных заявок.")
        return

    text = "📋 Список заявок:\n\n"
    for ticket in tickets:
        text += f"🆔 {ticket['ticket_id']} | 👤 {ticket['user_id']} | 🔖 {ticket['status']}\n📩 {ticket['text']}\n\n"

    await message.answer(text)
    await message.answer("Введите ID заявки, чтобы начать работу с ней.", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]]
    ))

# Выбор заявки оператором
@router.message()
async def select_ticket(message: types.Message):
    print('called select_ticket')
    operator_id = message.from_user.id
    ticket_id = -1
    if message.text.isdigit():
        ticket_id = int(message.text)

    ticket = await get_ticket_by_id(ticket_id)
    if not ticket:
        await message.answer("❌ Заявка не найдена.")
        return

    await update_ticket_status(ticket_id, "в работе")
    await set_user_state(operator_id, "working_on_ticket")  # Смена состояния оператора
    await message.answer(f"✅ Вы выбрали заявку #{ticket_id}. Общение начато.", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Закрыть заявку", callback_data=f"close_ticket_{ticket_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_from_ticket_{ticket_id}")]
        ]
    ))

    await bot.send_message(ticket["user_id"], f"🛠 Ваша заявка #{ticket_id} теперь в работе. Оператор свяжется с вами.")


@router.callback_query(lambda c: c.data.startswith("back_from_ticket_"))
async def back_from_ticket(callback: types.CallbackQuery):
    operator_id = callback.from_user.id
    ticket_id = callback.data.split("_")[2]

    await set_user_state(operator_id, "idle")  # 🔹 Возвращаем оператору состояние "idle"
    await callback.message.answer("🔙 Вы вернулись в главное меню оператора.", reply_markup=admin_keyboard())


# Закрытие заявки
@router.callback_query(lambda c: c.data.startswith("close_ticket_"))
async def close_ticket(callback: types.CallbackQuery):
    ticket_id = callback.data.split("_")[2]
    await update_ticket_status(ticket_id, "закрыта")

    await callback.message.answer(f"✅ Заявка #{ticket_id} закрыта.")
    ticket = await get_ticket_by_id(ticket_id)
    await bot.send_message(ticket["user_id"], f"✅ Ваша заявка #{ticket_id} закрыта.")

# Добавление оператора
@router.message(lambda msg: msg.text.find('Добавить оператора') != -1)
async def add_operator(message: types.Message):
    await message.answer("Введите ID пользователя, которого хотите сделать оператором:")

@router.message()
async def process_add_operator(message: types.Message):
    print('called process_add_operator')
    user_id = int(message.text)

    user_role = await get_user_role(user_id)
    if user_role == "operator":
        await message.answer("⚠️ Этот пользователь уже оператор.")
        return

    if user_role is None:
        await add_admin_user(user_id, "operator")
        await message.answer(f"✅ Пользователь {user_id} добавлен в базу и стал оператором.")
    else:
        await set_user_role(user_id, "operator")
        await message.answer(f"✅ Пользователь {user_id} теперь оператор.")

    await bot.send_message(user_id, "🎉 Вас назначили оператором! Теперь у вас есть доступ к управлению заявками.")