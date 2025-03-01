from aiogram import Router, types
from database import get_user_state, get_ticket_by_id, is_operator, find_operator_for_ticket


chat_router = Router()


@chat_router.message()
async def relay_messages(message: types.Message):
    print("Начато общение")
    user_id = message.from_user.id
    print(user_id)
    state = await get_user_state(user_id)
    print(state)
    if not state or not state.startswith("chating_"):
        return

    ticket_id = int(state.split("_")[1])
    ticket = await get_ticket_by_id(ticket_id)
    print(ticket)
    if not ticket:
        return
    if await is_operator(user_id):
        target_id = ticket["user_id"]
        print(f"Отправляет оператор {target_id}")
        sender = "Оператор"
    else:
        target_id = ticket["operator_id"]
        print(f"Отправляет Пользователь {target_id}")
        sender = "Пользователь"
    print("общение 2")
    from Bot import bot
    await bot.send_message(target_id, f"📩 {sender}: {message.text}")