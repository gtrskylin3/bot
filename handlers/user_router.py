import phonenumbers
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import exc, select, delete
from database.models import User, Service
from database.orm_query import get_or_create_user, deactivate_user, create_booking, get_user_bookings, update_phone, check_user_phone

from keyboards.user_menu import set_user_menu
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, ChatMemberUpdated, \
    InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Contact, ReplyKeyboardRemove, ResultChatMemberUnion, ForceReply
from aiogram.filters import CommandStart, Command, or_f, StateFilter
import keyboards.user_kb as user_kb
from handlers.user_text import START_TEXT
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from filters.admin_filter import admin
from datetime import datetime
from filters.month_filter import month_filter
import os
import logging

# logger = logging.getLogger(__name__)


class Signup(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_date = State()
    waiting_for_time = State()
    
CHANNEL_ID = -1002726677960

user_router = Router()
user_router.startup.register(set_user_menu)
image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "start.webp")
image = FSInputFile(image_path, filename='olesya.webp')


@user_router.message(CommandStart())
async def start(message: Message, session: AsyncSession):
    try:
        from_user = message.from_user
        user = await get_or_create_user(session, from_user.id, from_user.full_name)
        await message.answer_photo(photo=image, caption=START_TEXT, reply_markup=user_kb.start_kb.as_markup())
    except Exception as e:
        logging.exception("Ошибка при добавлении/получении пользователя:")

@user_router.message(Command(commands='help'))
async def help_cmd(message: Message):
    await message.answer('Это бот где <b>вы можете</b>:\n\nПолучать уведомления об эфирах\n'
    'Изучить доступные услуги и цены\n\n<b>Все просто и удобно❤</b>', reply_markup=user_kb.start_kb.as_markup())

@user_router.callback_query(F.data=='service_list')
async def service_list(callback: CallbackQuery, session: AsyncSession):    
    # Получаем активные услуги из базы данных
    services = await session.scalars(select(Service).where(Service.is_active == True))
    services_list = services.all()
    
    # await callback.message.delete()

    if services_list:
        for service in services_list:
            signup_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='Записаться', callback_data=f'signup_{service.id}')]
            ])
            text = f'<b>{service.name}</b>\n\n'
            text += f'📝<b>Описание:</b>\n{service.description}\n\n'
            text += f'💰<b>Цена:</b> {service.price} ₽\n'
            if service.duration > 60:
                text += f'⏱<b>Длительность:</b> {(service.duration / 60):.2f} ч.\n\n'
            else:
                text += f'⏱<b>Длительность:</b> {service.duration} мин.\n\n'
            await callback.message.answer(text, reply_markup=signup_kb)
    else:
        await callback.message.answer('В данный момент услуги не доступны😞\n<b>Попробуйте позже</b>')
        await callback.answer('')
        return
    
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
        logging.warning("Пользователь заблокировал бота: %s", tg_id)
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
    print(current_state)
    if current_state and current_state.startswith('Signup:'):
        await state.clear()
        await message.answer(
            "❌ Запись отменена\n\n"
            "Вы можете начать новую запись, выбрав услугу в меню.",
            reply_markup=user_kb.back_mrk
        )
    else:
        await message.answer("Нет активной записи для отмены", reply_markup=ReplyKeyboardRemove())

@user_router.callback_query(F.data.startswith('signup_'))
async def start_signup(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    book_user = await get_user_bookings(session, user_id=callback.from_user.id)
    if book_user >= 3:
        logging.info(f'У user: {callback.from_user.id} пытается сделать больше 3 записей')
        await callback.message.answer("Вы не можете сделать больше трёх записей\nПожалуйста подождите я c вами свяжусь")
        await callback.answer('Более 3 записей недопустимо')
        return
    service_id = int(callback.data.split('_')[1])
    service = await session.scalar(select(Service).where(Service.id == service_id))
    
    if service:
        await state.update_data(service_id=service_id, service_name=service.name, service_price=service.price)
        await state.set_state(Signup.waiting_for_name)
        await callback.message.answer(
            f"📝 <b>Запись на услугу: {service.name}</b>\n\n"
            f"💰 <b>Стоимость:</b> {service.price} ₽\n\n"
            f"Пожалуйста, введите ваше имя:\n\n"
            f"<i>Для отмены записи введите /cancel</i>",
            reply_markup=ForceReply(selective=True, input_field_placeholder="Введите ваше имя")
        )
        await callback.answer()
    else:
        await callback.message.answer("❌ Услуга не найдена")
        await callback.answer()

@user_router.message(F.text.isalpha(), Signup.waiting_for_name)
async def get_name(message: Message, state: FSMContext, session: AsyncSession):
    name = message.text.strip().title()
    if len(name) < 2:
        await message.answer("❌ Имя должно содержать минимум 2 символа. Попробуйте снова:", reply_markup=ForceReply(selective=True, input_field_placeholder="Введите имя (минимум 2 символа)"))
        return
    
    await state.update_data(name=name)
    phone = await check_user_phone(session, message.from_user.id)
    if not phone:
        await state.set_state(Signup.waiting_for_phone)
        
        await message.answer(
            "📞 Введите ваш номер телефона:\n\n"
            "<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>\n\n"
            "<i>Или нажмите кнопку ниже, чтобы поделиться контактом</i>\n\n"
            "<i>Для отмены записи введите /cancel</i>",
            reply_markup=user_kb.contact_kb
        )
        return
    await state.update_data(phone=phone)
    await state.set_state(Signup.waiting_for_date)
    await message.answer(f"Ваш номер для записи: {phone}\n\n"
                         "📅 Введите предпочитаемую дату:\n\n"
                         "<i>Формат: ДД.ММ (например: 15.01)</i>\n\n"
                         "<i>Для отмены записи введите /cancel</i>",
                         
                            reply_markup=ForceReply(selective=True, input_field_placeholder="Введите дату"))

@user_router.message(Signup.waiting_for_phone)
async def get_phone(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    if message.contact:
        contact: Contact = message.contact
        # Сохраняем данные контакта
        phone=contact.phone_number
        if phone.startswith('8') or phone.startswith('7'):
            phone = '+7' + phone[1:]
        await update_phone(session, message.from_user.id, phone)
        await state.update_data(
            phone=phone,
            contact_first_name=contact.first_name,
            contact_last_name=contact.last_name
        )
        await state.set_state(Signup.waiting_for_date)
    else:
        phone = message.text.strip()
        if phone.startswith('8'):
            phone = '+7' + phone[1:]
        phone = phone.replace(' ', '')
        try:
            parsed_phone = phonenumbers.parse(phone, "RU")
            if not phonenumbers.is_valid_number(parsed_phone):
                await message.answer("❌ Неверный формат номера телефона. Попробуйте снова:\n\n<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>",
                reply_markup=ForceReply(selective=True, 
                input_field_placeholder="Введите номер телефона")
                )
                return
            
            await state.update_data(phone=phone)
            await update_phone(session, message.from_user.id, phone)
            await state.set_state(Signup.waiting_for_date)
            #валидация телефона
        except phonenumbers.NumberParseException:
            await message.answer("❌ Неверный формат номера телефона. Попробуйте снова:\n\n<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>",
                reply_markup=ForceReply(selective=True, 
                input_field_placeholder="Введите номер телефона")
                )
            return
    await message.answer(
    "📅 Введите предпочитаемую дату:\n\n"
    "<i>Формат: ДД.ММ (например: 15.01)</i>\n\n"
    "<i>Для отмены записи введите /cancel</i>",
    reply_markup=ReplyKeyboardRemove()
    )

@user_router.callback_query(F.data=="change_user_phone", Signup.waiting_for_date)
async def change_user_phone(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.set_state(Signup.waiting_for_phone)
        
    await callback.message.answer(
        "📞 Введите ваш новый номер телефона:\n\n"
        "<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>\n\n"
        "<i>Или нажмите кнопку ниже, чтобы поделиться контактом</i>\n\n"
        "<i>Для отмены записи введите /cancel</i>",
        reply_markup=user_kb.contact_kb
    )

@user_router.message(F.text.split('.'), Signup.waiting_for_date)
async def get_date(message: Message, state: FSMContext):
    date_text = message.text.strip()
    current_date = datetime.now()
    
    # Простая валидация даты
    try:
        # Парсим введенную дату (добавляем текущий год)
        input_date = datetime.strptime(f"{date_text}.{current_date.year}", '%d.%m.%Y')
        # Проверяем, что дата не в прошлом
        if input_date.date() < current_date.date():
            await message.answer("❌ Вы не можете выбрать прошедшую дату. Попробуйте снова:\n\n<i>Формат: ДД.ММ (например: 15.01)</i>",
            reply_markup=ForceReply(input_field_placeholder="Введите дату:", selective=True))
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
            "<i>Для отмены записи введите /cancel</i>",
            reply_markup=ForceReply(selective=True, input_field_placeholder="Введите время, например: 14:00")
        )
        
    except ValueError:
        await message.answer("❌ Неверный формат даты. Попробуйте снова:\n\n<i>Формат: ДД.ММ (например: 15.01)</i>",
        reply_markup=ForceReply(input_field_placeholder="Введите дату через ."))
        return
    
    

@user_router.message(Signup.waiting_for_time)
async def get_time(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    time_text = message.text.strip()
    # Простая валидация времени
    try:
        datetime.strptime(time_text, '%H:%M')
    except ValueError:
        await message.answer("❌ Неверный формат времени. Попробуйте снова:\n\n<i>Формат: ЧЧ:ММ (например: 14:00)</i>", reply_markup=ForceReply(selective=True, input_field_placeholder="Введите время, например: 14:00"))
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
            logging.exception(f"Ошибка отправки уведомления админу, data: {data}")
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
        logging.exception(f"Ошибка создания записи, user: {message.from_user.id}, data: {data}")
    await state.clear()


@user_router.message()
async def spam(message: Message):
    await message.answer('Воспользуйтесь меню для навигации', reply_markup=user_kb.back_mrk)

