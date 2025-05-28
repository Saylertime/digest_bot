from aiogram import Router
from aiogram.filters import CommandStart

from pg_maker import add_user

router_start = Router()


@router_start.message(CommandStart())
async def command_start_handler(message):
    if message.chat.type == "private":
        telegram_id = str(message.from_user.id)
    else:
        telegram_id = str(message.chat.id)

    await add_user(telegram_id=telegram_id)
    await message.answer(f"Йо! Дайджест приходит в 21:00 каждый день")
