import os
from aiogram import Bot
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from database import (
    get_all_tickets, update_ticket_status, get_ticket_by_id, set_user_role, get_user_role,
    add_admin_user, set_user_state, is_operator, get_user_state
)
from dotenv import load_dotenv

router = Router()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

def admin_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Все заявки")],
        [KeyboardButton(text="👤 Добавить оператора")],
    ], resize_keyboard=True, one_time_keyboard=True)


@router.message(lambda msg: msg.text == "📋 Все заявки")
async def view_open_tickets(message: types.Message):
    user_id = message.from_user.id
    if not await is_operator(user_id):
        return
    tickets = await get_all_tickets()
    if not tickets:
        await message.answer("📭 Нет активных заявок.")
        return
    text = "📋 Открытые заявки:\n\n"
    for ticket in tickets:
        text += f"🆔 {ticket['ticket_id']} | 👤 {ticket['user_id']}\n📩 {ticket['text'][:100]}\n\n"

    await message.answer(text)
    await message.answer("Введите ID заявки, чтобы начать работу с ней:")


@router.message(lambda msg: msg.text.isdigit())
async def select_ticket(message: types.Message):
    operator_id = message.from_user.id
    ticket_id = int(message.text)

    ticket = await get_ticket_by_id(ticket_id)
    if not ticket:
        await message.answer("❌ Заявка не найдена.")
        return
    await update_ticket_status(ticket_id, "в работе")
    await set_user_state(operator_id, f"working_on_ticket_{ticket_id}")
    user_id = ticket["user_id"]
    await set_user_state(operator_id, f"chating_{ticket_id}")
    await set_user_state(user_id, f"chating_{ticket_id}")
    await message.answer(
        f"✅ Вы выбрали заявку #{ticket_id}. Теперь вы можете общаться с пользователем.\n"
        "Нажмите '✅ Закрыть заявку', когда работа будет завершена.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Закрыть заявку", callback_data=f"close_ticket_{ticket_id}")]
        ])
    )

    await router.bot.send_message(user_id,
                                  f"🛠 Ваша заявка #{ticket_id} теперь в работе. Оператор свяжется с вами.")


@router.callback_query(lambda c: c.data.startswith("close_ticket_"))
async def close_ticket(callback: types.CallbackQuery):
    ticket_id = int(callback.data.split("_")[2])
    operator_id = callback.from_user.id

    ticket = await get_ticket_by_id(ticket_id)
    await update_ticket_status(ticket_id, "закрыта")
    await set_user_state(operator_id, "idle")

    await callback.message.answer(f"✅ Заявка #{ticket_id} закрыта.")
