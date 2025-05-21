from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, and_f
import keyboards.admin_kb as admin_kb
from .user_router import users
import filters.admin_filter as Admin


admin_router = Router()
admin_router.message.filter(Admin.IsAdmin())

@admin_router.message(CommandStart())
async def admin_start(message: Message):
    await message.answer('Вы админисктратор вы можете cделать:', reply_markup=admin_kb.admin_kb.as_markup())

@admin_router.message(Admin.IsAdmin())
async def admin_message(message: Message):
    await message.answer(text='Привет админ')


