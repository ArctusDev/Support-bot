import os
from aiogram import Bot
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from database import (
    get_all_tickets, update_ticket_status, get_ticket_by_id, set_user_role, get_user_role,
    add_admin_user, set_user_state, is_operator, get_user_state, init_db, clear_user_state
)
from dotenv import load_dotenv

admin_router = Router()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
DB_URL = os.getenv("DB_URL")

def admin_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Все заявки")],
        [KeyboardButton(text="👤 Добавить оператора")],
    ], resize_keyboard=True, one_time_keyboard=True)



@admin_router.message(lambda msg: msg.text == "📋 Все заявки")
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
    await set_user_state(user_id, f"select_ticket")
    await message.answer("Введите ID заявки, чтобы начать работу с ней:")


@admin_router.callback_query(lambda c: c.data.startswith("close_ticket_"))
async def close_ticket(callback: types.CallbackQuery):
    ticket_id = int(callback.data.split("_")[2])
    ticket = await get_ticket_by_id(ticket_id)
    operator_id = callback.from_user.id
    user_id = ticket["user_id"]
    await update_ticket_status(ticket_id, "закрыта")
    await set_user_state(operator_id, "idle")
    await set_user_state(user_id, "idle")

    await callback.message.answer(f"✅ Заявка #{ticket_id} закрыта.")
    await bot.send_message(user_id,
                           f"🛠 Ваша заявка #{ticket_id} закрыта.")


@admin_router.message(lambda msg: msg.text == "👤 Добавить оператора")
async def add_operator_request(message: types.Message):
    print('Оператор нажал кнопку добавить оператора')
    operator_id = message.from_user.id
    if not await is_operator(operator_id):
        return
    await set_user_state(operator_id, "wating_for_operator_id")
    await message.answer("Введите ID пользователя")

@admin_router.message(lambda msg: msg.text.isdigit())
async def confirm_operator(message: types.Message):
    operator_id = message.from_user.id
    print(operator_id)
    state = await get_user_state(operator_id)
    if state == "wating_for_operator_id":
        target_user_id = message.text.strip()

        if not target_user_id.isdigit():
            await message.answer("⚠️ Ошибка! Введите корректный ID пользователя (число).")
            return

        target_user_id = int(target_user_id)
        user_role = await get_user_role(target_user_id)
        if not await get_user_role(target_user_id):
            await message.answer("⚠️ Не найден пользователь.")
            return

        if user_role == "operator":
            await message.answer("⚠️ Этот пользователь уже является оператором.")
            await set_user_state(operator_id, "idle")
            return

        # ✅ Записываем состояние с ID пользователя
        await set_user_state(operator_id, f"confirm_operator_{target_user_id}")

        # Кнопки подтверждения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_operator_{target_user_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_operator")]
        ])

        await message.answer(
            f"⚠️ Вы уверены, что хотите сделать пользователя {target_user_id} оператором?",
            reply_markup=keyboard, parse_mode="Markdown"
        )
    elif state == "select_ticket":
        operator_id = message.from_user.id
        ticket_id = int(message.text)
        ticket = await get_ticket_by_id(ticket_id)
        print(ticket["user_id"])
        if not ticket:
            await message.answer("❌ Заявка не найдена.")
            return
        await update_ticket_status(ticket_id, "в работе")
        await set_user_state(operator_id, f"working_on_ticket_{ticket_id}")
        user_id = ticket["user_id"]
        await set_user_state(operator_id, f"chating_{ticket_id}")
        await set_user_state(user_id, f"chating_{ticket_id}")

        conn = await init_db()
        await conn.execute("UPDATE tickets SET operator_id = $1 WHERE ticket_id = $2", operator_id, ticket_id)
        await conn.close()

        await message.answer(
            f"✅ Вы выбрали заявку #{ticket_id}. Теперь вы можете общаться с пользователем.\n"
            "Нажмите '✅ Закрыть заявку', когда работа будет завершена.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Закрыть заявку", callback_data=f"close_ticket_{ticket_id}")]
            ])
        )

        await bot.send_message(user_id,
                               f"🛠 Ваша заявка #{ticket_id} теперь в работе. Оператор свяжется с вами.")
    else:
        user_id = message.from_user.id
        if await is_operator(user_id):
            return
        state = await get_user_state(user_id)
        if not state.startswith("chating_"):
            await message.answer("❌ Я вас не понял. Используйте кнопки в меню.")

@admin_router.callback_query(lambda c: c.data.startswith("confirm_operator_"))
async def process_operator_confirmation(callback: types.CallbackQuery):
    """Подтверждение назначения оператора"""
    admin_id = callback.from_user.id
    target_user_id = int(callback.data.split("_")[2])

    user_role = await get_user_role(target_user_id)

    if user_role is None:
        await add_admin_user(target_user_id, "operator")
    else:
        await set_user_role(target_user_id, "operator")

    await set_user_state(target_user_id, "idle")  # Очищаем состояние у нового оператора
    await set_user_state(admin_id, "idle")  # Очищаем состояние у текущего оператора

    await callback.message.edit_text(f"✅ Пользователь {target_user_id} теперь оператор.")

    # Обновляем меню нового оператора
    await bot.send_message(
        target_user_id,
        "🎉 Вас назначили оператором! Теперь у вас есть доступ к управлению заявками.",
        reply_markup=admin_keyboard()
    )


@admin_router.callback_query(lambda c: c.data == "cancel_operator")
async def cancel_operator(callback: types.CallbackQuery):
    """Отмена добавления оператора"""
    admin_id = callback.from_user.id
    await clear_user_state(admin_id)  # Очищаем состояние
    await callback.message.edit_text("❌ Операция отменена.")