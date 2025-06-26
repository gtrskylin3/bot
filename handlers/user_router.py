from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from database.models import User, Service
from database.orm_query import get_or_create_user, deactivate_user, create_booking

from keyboards.user_menu import set_user_menu
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, ChatMemberUpdated, \
    InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Contact, ReplyKeyboardRemove, ResultChatMemberUnion
from aiogram.filters import CommandStart, Command, or_f, StateFilter
import keyboards.user_kb as user_kb
from handlers.user_text import START_TEXT
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from filters.admin_filter import admin
from datetime import datetime
from filters.month_filter import month_filter

class Signup(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_date = State()
    waiting_for_time = State()
    
CHANNEL_ID = -1002726677960

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
    # await callback.message.delete()

    if services_list:
        for service in services_list:
            signup_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='Записаться', callback_data=f'signup_{service.id}')]
            ])
            text = f'<b>{service.name}</b>\n\n'
            text += f'📝<b>Описание:</b>\n{service.description}\n'
            text += f'💰<b>Цена:</b> {service.price} ₽\n'
            if service.duration > 60:
                text += f'⏱<b>Длительность:</b> {(service.duration / 60):.2f} ч.\n\n'
            else:
                text += f'⏱<b>Длительность:</b> {service.duration} мин.\n\n'
            await callback.message.answer(text, reply_markup=signup_kb)
    else:
        text = 'В данный момент услуги не доступны. Обратитесь к администратору.'
    
    await callback.message.answer('Выберите услугу или вернитесь в меню', reply_markup=user_kb.back_mrk)
    await callback.answer('Мои услуги')

@user_router.callback_query(F.data=='back')
async def back(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer('')
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
async def sub_cmd(message: Message):
    await message.answer('Чтобы получить <b>подарок</b> 🎁\n<b>Подпишитесь на мой канал 👇</b>', reply_markup=user_kb.sub_kb)



def check_sub_channel(chat_member):
    return chat_member.status != 'left'


@user_router.callback_query(F.data=='check_sub')
async def gift_cmd(callback: CallbackQuery, bot: Bot):
    await callback.answer('')
    await callback.message.delete()
    chat_member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=callback.from_user.id)
    if not check_sub_channel(chat_member):
        await callback.message.answer("Вы не подписаны на канал\n<b>Подпишитесь чтобы получить подарок🎁 👇</b>", reply_markup=user_kb.sub_kb)
        return
    else:
        await callback.message.answer("Чтобы получить <b>подарок</b> 🎁\n<b>Жмите на кнопку ниже 👇</b>\n", 
        reply_markup=user_kb.gift_kb)

@user_router.message(Command('cancel'))
async def cancel_signup(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state and current_state.startswith('Signup:'):
        await state.clear()
        await message.answer(
            "❌ Запись отменена\n\n"
            "Вы можете начать новую запись, выбрав услугу в меню.",
            reply_markup=user_kb.back_mrk
        )
    else:
        await message.answer("Нет активной записи для отмены")

@user_router.callback_query(F.data.startswith('signup_'))
async def start_signup(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    service_id = int(callback.data.split('_')[1])
    service = await session.scalar(select(Service).where(Service.id == service_id))
    
    if service:
        await state.update_data(service_id=service_id, service_name=service.name, service_price=service.price)
        await state.set_state(Signup.waiting_for_name)
        await callback.message.answer(
            f"📝 <b>Запись на услугу: {service.name}</b>\n\n"
            f"💰 <b>Стоимость:</b> {service.price} ₽\n\n"
            f"Пожалуйста, введите ваше имя:\n\n"
            f"<i>Для отмены записи введите /cancel</i>"
        )
        await callback.answer()
    else:
        await callback.message.answer("❌ Услуга не найдена")
        await callback.answer()

@user_router.message(F.text, Signup.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("❌ Имя должно содержать минимум 2 символа. Попробуйте снова:")
        return
    
    await state.update_data(name=message.text.strip())
    await state.set_state(Signup.waiting_for_phone)
    contact_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Поделиться контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "📞 Введите ваш номер телефона:\n\n"
        "<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>\n\n"
        "<i>Или нажмите кнопку ниже, чтобы поделиться контактом</i>\n\n"
        "<i>Для отмены записи введите /cancel</i>",
        reply_markup=contact_kb
    )

@user_router.message(Signup.waiting_for_phone)
async def get_phone(message: Message, state: FSMContext, bot: Bot):
    if message.contact:
        contact: Contact = message.contact
        # Сохраняем данные контакта
        await state.update_data(
            phone=contact.phone_number,
            contact_first_name=contact.first_name,
            contact_last_name=contact.last_name
        )
        await state.set_state(Signup.waiting_for_date)
    else:
        try:
            phone = message.text.strip()
            # Простая валидация телефона
            if not (phone.startswith('+7') or phone.startswith('8')) or len(phone) < 10:
                await message.answer("❌ Неверный формат номера телефона. Попробуйте снова:\n\n<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>")
                return
            if phone.startswith('8'):
                phone = '+7' + phone[1:]
            phone = phone.replace(' ', '')
            await state.update_data(phone=phone)
            await state.set_state(Signup.waiting_for_date)
        except:
            await message.answer("❌ Неверный формат номера телефона. Попробуйте снова:\n\n<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>")
            return
    await message.answer(
    "📅 Введите предпочитаемую дату:\n\n"
    "<i>Формат: ДД.ММ (например: 15.01)</i>\n\n"
    "<i>Для отмены записи введите /cancel</i>",
    reply_markup=ReplyKeyboardRemove()
    )

@user_router.message(Signup.waiting_for_date)
async def get_date(message: Message, state: FSMContext):
    date_text = message.text.strip()
    # Простая валидация даты
    try:
        datetime.strptime(date_text, '%d.%m')
    except ValueError:
        await message.answer("❌ Неверный формат даты. Попробуйте снова:\n\n<i>Формат: ДД.ММ (например: 15.01)</i>")
        return
    
    date_text = date_text.split('.')
    if len(date_text[1]) == 1:
        date_text[1] = '0' + date_text[1]
    date_text[1] = month_filter[date_text[1]]
    date_text = ' '.join(date_text)
    await state.update_data(preferred_date=date_text)
    await state.set_state(Signup.waiting_for_time)
    await message.answer(
        "🕐 Введите предпочитаемое время:\n\n"
        "<i>Формат: ЧЧ:ММ (например: 14:00)</i>\n\n"
        "<i>Для отмены записи введите /cancel</i>"
    )

@user_router.message(Signup.waiting_for_time)
async def get_time(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    time_text = message.text.strip()
    # Простая валидация времени
    try:
        datetime.strptime(time_text, '%H:%M')
    except ValueError:
        await message.answer("❌ Неверный формат времени. Попробуйте снова:\n\n<i>Формат: ЧЧ:ММ (например: 14:00)</i>")
        return
    
    await state.update_data(preferred_time=time_text)
    data = await state.get_data()
    try:
        booking = await create_booking(
            session=session,
            user_tg_id=message.from_user.id,
            service_id=data['service_id'],
            client_name=data['name'],
            phone=data['phone'],
            preferred_date=data['preferred_date'],
            preferred_time=data['preferred_time']
        )   
        # Уведомляем админа
        admin_text = f"🎯 <b>Новая запись на услугу!</b>\n\n"
        admin_text += f"👤 <b>Клиент:</b> {data['name']}\n"
        admin_text += f"🆔 <b>Telegram ID:</b> {message.from_user.id}\n"
        admin_text += f"📞 <b>Телефон:</b> {data['phone']}\n"
        admin_text += f"🎯 <b>Услуга:</b> {data['service_name']}\n"
        admin_text += f"💰 <b>Стоимость:</b> {data['service_price']} ₽\n"
        admin_text += f"📅 <b>Дата:</b> {data['preferred_date']}\n"
        admin_text += f"🕐 <b>Время:</b> {data['preferred_time']}\n"
        
        try:
            await bot.send_message(chat_id=admin, text=admin_text)
            if 'contact_first_name' in data:
                await bot.send_contact(
                    chat_id=admin,
                    phone_number=data['phone'], 
                    first_name=data['contact_first_name'], 
                    last_name=data['contact_last_name'])
            else:
                await bot.send_contact(
                    chat_id=admin, 
                    phone_number=data['phone'], 
                    first_name=data['name']
                    )
        except Exception as admin_error:
            print(f"Ошибка отправки уведомления админу: {admin_error}")
            await message.answer(
                "❌ Произошла ошибка при создании записи. Попробуйте позже.",
                reply_markup=user_kb.back_mrk
            )
            return

        await message.answer(
            "✅ <b>Запись успешно создана!</b>\n\n"
            f"🎯 <b>Услуга:</b> {data['service_name']}\n"
            f"💰 <b>Стоимость:</b> {data['service_price']} ₽\n"
            f"📅 <b>Дата:</b> {data['preferred_date']}\n"
            f"🕐 <b>Время:</b> {data['preferred_time']}\n\n"
            "📞 Я свяжусь с вами для подтверждения записи.\n\n"
            "Спасибо за доверие! ❤️",
            reply_markup=user_kb.back_mrk
        )
    except Exception as e:
        await message.answer(
            "❌ Произошла ошибка при создании записи. Попробуйте позже.",
            reply_markup=user_kb.back_mrk
        )
        print(f"Ошибка создания записи: {e}")
    await state.clear()


@user_router.message()
async def spam(message: Message):
    await message.answer('Воспользуйтесь меню для навигации', reply_markup=user_kb.back_mrk)

