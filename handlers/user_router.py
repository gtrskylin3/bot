from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from database.models import User, Service
from database.orm_query import get_or_create_user, deactivate_user

from keyboards.user_menu import set_user_menu
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, ChatMemberUpdated
from aiogram.filters import CommandStart, Command, or_f
import keyboards.user_kb as user_kb
from handlers.user_text import START_TEXT



user_router = Router()
user_router.startup.register(set_user_menu)
image = FSInputFile("start.webp", filename='olesya.webp')


@user_router.message(CommandStart())
async def start(message: Message, session: AsyncSession):
    from_user = message.from_user
    user = await get_or_create_user(session, from_user.id, from_user.full_name)
    await message.answer_photo(photo=image, caption=START_TEXT, reply_markup=user_kb.start_kb.as_markup())


@user_router.message(Command(commands='help'))
async def help_cmd(message: Message):
    await message.answer('Это бот где <b>вы можете</b>:\n\nПолучать уведомления об эфирах\n'
    'Изучить доступные услуги и цены\n\n<b>Все просто и удобно❤</b>', reply_markup=user_kb.start_kb.as_markup())

@user_router.callback_query(F.data=='service_list')
async def service_list(callback: CallbackQuery, session: AsyncSession):    
    # Получаем активные услуги из базы данных
    services = await session.scalars(select(Service).where(Service.is_active == True))
    services_list = list(services)
    
    if services_list:
        text = '<b>Мои услуги:</b>\n\n'
        for service in services_list:
            text += f'<b>{service.name}</b>\n'
            text += f'📝 {service.description}\n'
            text += f'💰 {service.price} ₽\n'
            if service.duration > 60:
                text += f'⏱ {(service.duration / 60):.2f} ч.\n\n'
            else:
                text += f'⏱ {service.duration} мин.\n\n'
    else:
        text = 'В данный момент услуги не доступны. Обратитесь к администратору.'
    
    await callback.message.answer(text, reply_markup=user_kb.back_mrk)
    await callback.answer('Мои услуги')

@user_router.callback_query(F.data=='back')
async def back(callback: CallbackQuery):
    await callback.message.answer_photo(photo=image, caption=START_TEXT, 
    reply_markup=user_kb.start_kb.as_markup())



@user_router.my_chat_member()
async def handle_my_chat_member(event: ChatMemberUpdated, session: AsyncSession):
    """
    Удаляет пользователя из базы, если он заблокировал бота (status = 'kicked' или 'left').
    """
    if event.new_chat_member.status in ("kicked", "left"):  # kicked - заблокировал, left - удалил
        tg_id = event.from_user.id
        await deactivate_user(session, tg_id)
        # await session.execute(delete(User).where(User.tg_id == tg_id))
        # await session.commit()

@user_router.message(Command('gift'))
async def gift_cmd(message: Message):
    await message.answer("Чтобы получить <b>подарок</b> 🎁\n<b>Жмите на кнопку ниже 👇</b>\n", 
    reply_markup=user_kb.gift_kb)


@user_router.message()
async def spam(message: Message):
    await message.answer('Воспользуйтесь меню для навигации')

