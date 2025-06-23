from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, Service
from keyboards.user_menu import set_user_menu
from aiogram.filters import CommandStart, Command, or_f
import keyboards.user_kb as user_kb
from database.orm_query import get_or_create_user


user_router = Router()
user_router.startup.register(set_user_menu)
image = FSInputFile("start.webp", filename='olesya.webp')


@user_router.message(CommandStart())
async def start(message: Message, session: AsyncSession):
    from_user = message.from_user
    user = await get_or_create_user(session, from_user.id, from_user.full_name)
    await message.answer_photo(photo=image, caption='Привет я Чернова Олеся <b>Психолог</b>\n' \
    'Работаю со взрослыми и детьми!❤\nИндивидуально и в группах.\n<b>Конфиденциально!</b>\n<b>Безопасно!</b>\n<b>Онлайн и оффлайн.</b>', reply_markup=user_kb.start_kb.as_markup())


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
    await callback.message.answer_photo(photo=image, caption='Привет я Чернова Олеся <b>Психолог</b>\n' \
    'Работаю со взрослыми и детьми!❤\nИндивидуально и в группах.\n<b>Конфиденциально!</b>\n<b>Безопасно!</b>\n<b>Онлайн и оффлайн.</b>', reply_markup=user_kb.start_kb.as_markup())

@user_router.message()
async def spam(message: Message):
    await message.answer('Воспользуйтесь меню для навигации')

