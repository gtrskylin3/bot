from aiogram import Router, F, Bot
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

@admin_router.callback_query(F.data=='send_all')
async def send_all(callback: CallbackQuery, bot: Bot):
    await callback.message.delete()
    await callback.answer('')
    if users:
        for user in users:
            await bot.send_message(chat_id=users[user], text='Hello')
        callback.message.answer("Рассылка прошла успешно")
    else:
        await callback.message.answer('Список пользователей пуст\nПопробуйте ещё раз', reply_markup=admin_kb.admin_kb.as_markup())
        
@admin_router.callback_query(F.data=='user_list')
async def send_all(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer('')
    if users:
        for user in users:
            await callback.message.answer(text=f"Имя пользователя: {user}, ID пользователя: {users[user]}")
        await callback.message.answer("Рассылка прошла успешно")
    else:
        await callback.message.answer('Список пользователей пуст\nПопробуйте ещё раз', reply_markup=admin_kb.admin_kb.as_markup())
        
        

@admin_router.message()
async def admin_message(message: Message):
    await message.answer(text='Привет админ')


