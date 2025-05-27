from aiogram import Router
from aiogram.filters import CommandStart

from pg_maker import add_user

router_start = Router()


@router_start.message(CommandStart())
async def command_start_handler(message):
    await add_user(telegram_id=str(message.from_user.id))
    await message.answer(f"Йо! Дайджест приходит в 21:00 каждый день")
