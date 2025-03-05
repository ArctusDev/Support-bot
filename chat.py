from aiogram import Router, types
from database import get_user_state, get_ticket_by_id, is_operator, set_user_state

chat_router = Router()

@chat_router.message()
async def relay_messages(message: types.Message):
    print("Начато общение")
    user_id = message.from_user.id
    print(user_id)
    state = await get_user_state(user_id)
    if not state or not state.startswith("chating_"):
        from Bot import main_menu, admin_keyboard
        if await is_operator(user_id):
            await message.answer("❌ Я вас не понял. Используйте кнопки в меню.", reply_markup=admin_keyboard())
        else:
            await message.answer("❌ Я вас не понял. Используйте кнопки в меню.", reply_markup=main_menu())
        return

    ticket_id = int(state.split("_")[1])
    ticket = await get_ticket_by_id(ticket_id)
    if not ticket:
        return
    if await is_operator(user_id):
        target_id = ticket["operator_id"]
        if target_id == ticket["user_id"]:
            await message.answer("❌ Это ваша заявка, вы не можете на неё отвечать")
            await set_user_state(user_id, state='idle')
            return
        print(f"Отправляет оператор {target_id}")
        sender = "Оператор"
    else:
        target_id = ticket["user_id"]
        print(f"Отправляет Пользователь {target_id}")
        sender = "Пользователь"
    print(message.text, message.caption)
    from Bot import bot
    if message.video:
        await bot.send_video(target_id, message.video.file_id, caption=message.caption)
    elif message.document:
        await bot.send_document(target_id, f"📩 {sender}:", message.document.file_id, caption=message.caption)
    elif message.photo:
        await bot.send_photo(target_id, message.photo[-1].file_id, caption=message.caption)
    elif message.text:
        await bot.send_message(target_id, f"📩 {sender}: {message.text}")
    else:
        await message.answer("❌ Недопустимый формат файла")