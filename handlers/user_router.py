from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
import keyboards.user_kb as user_kb

users = []
user_router = Router()

@user_router.message(CommandStart())
async def start(message: Message):
    users.append(message.chat.id)
    await message.answer(text='Привет я Чернова Олеся <b><i>психолог</i></b>', parse_mode='HTML', reply_markup=user_kb.start_kb.as_markup())
    print(users)
