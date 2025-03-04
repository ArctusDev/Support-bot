from aiogram import Router, types
from database import get_user_state, get_ticket_by_id, is_operator


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
    # if message.text and message.video:
    #     await bot.send_video(target_id, f"📩 {sender}:", message.text, message.video.file_id, caption=message.caption)
    # elif message.text and message.photo:
    #     await bot.send_message(target_id, f"📩 {sender}:", message.text, message.photo[-1], caption=message.caption)
    # elif message.text and message.document:
    #     await bot.send_message(target_id, f"📩 {sender}:", message.text, message.document.file_id, caption=message.caption)
    # elif message.video:
    #     await bot.send_message(target_id, f"📩 {sender}:", message.video.file_id, caption=message.caption)
    # elif message.document:
    #     await bot.send_message(target_id, f"📩 {sender}:", message.document.file_id, caption=message.caption)
    # if message.photo:
    #     await bot.send_photo(target_id, f"📩 {sender}:", message.photo[-1], caption=message.caption)
    elif message.text:
        await bot.send_message(target_id, f"📩 {sender}: {message.text}")
    else:
        await message.answer("❌ Недопустимый формат файла")