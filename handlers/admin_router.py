from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, and_f
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import keyboards.admin_kb as admin_kb
import filters.admin_filter as Admin
from database.models import User

admin_router = Router()
admin_router.message.filter(Admin.IsAdmin())

@admin_router.message(CommandStart())
async def admin_start(message: Message):
    await message.answer('Вы админисктратор вы можете cделать:', reply_markup=admin_kb.admin_kb.as_markup())

@admin_router.callback_query(F.data=='send_all')
async def send_all(callback: CallbackQuery, bot: Bot, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    users = await session.scalars(select(User).where(User.is_active==True))
    
    if users:
        for user in users:
            if user.is_active:
                await bot.send_message(chat_id=str(user.tg_id), text='Hello')
        await callback.message.answer("Рассылка прошла успешно")
    else:
        await callback.message.answer('Список пользователей пуст\nПопробуйте ещё раз', reply_markup=admin_kb.admin_kb.as_markup())
        
@admin_router.callback_query(F.data=='user_list')
async def send_all(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    users = await session.scalars(select(User))
    text = []
    if users:
        for user in users:
            status = 'Активный'
            if not user.is_active:
                status = 'Неактивный'
            text.append(f"Имя пользователя: {user.name}\nID пользователя: {user.tg_id}\nCтатус пользователя: <b>{status}</b>")
        await callback.message.answer(text='\n\n'.join(i for i in text))
    else:
        await callback.message.answer('Список пользователей пуст\nПопробуйте ещё раз', reply_markup=admin_kb.admin_kb.as_markup())
        
        

@admin_router.message()
async def admin_message(message: Message):
    await message.answer(text='Привет админ')


