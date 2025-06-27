from aiogram import Router, F, Bot
from aiogram.types import InlineKeyboardMarkup, Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import CommandStart, Command, and_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

import keyboards.admin_kb as admin_kb
import filters.admin_filter as Admin
from database.models import User, Service
from database.orm_query import get_all_bookings, delete_booking


class ServiceCreation(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_duration = State()


class DeleteService(StatesGroup):
    waiting_for_confirmation = State()

admin_router = Router()
admin_router.message.filter(Admin.IsAdmin())
admin_router.callback_query.filter(Admin.IsAdmin())

@admin_router.message(CommandStart())
async def admin_start(message: Message):
    await message.answer('Вы админисктратор вы можете cделать:', reply_markup=admin_kb.admin_kb.as_markup())


@admin_router.callback_query(F.data=='back_to_admin')
async def back_to_admin(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    print(current_state)
    if current_state is not None:
        await state.clear()
    await callback.message.delete()
    await callback.answer('')
    await callback.message.answer('Вы админисктратор вы можете cделать:', reply_markup=admin_kb.admin_kb.as_markup())

@admin_router.message(Command(commands='cancel'))
async def cancel_broadcast_settings(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer('Настройка отменена.', reply_markup=admin_kb.admin_kb.as_markup())
    else:
        await message.answer('Нет активного процесса настройки.')


@admin_router.callback_query(F.data=='user_list')
async def send_all(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    users = await session.scalars(select(User))
    users = users.all()
    text = []
    if users:
        for user in users:
            status = 'Активный'
            if not user.is_active:
                status = 'Неактивный'
            text.append(f"Имя пользователя: {user.name}\nID пользователя: {user.tg_id}\nCтатус пользователя: <b>{status}</b>")
        await callback.message.answer(text='\n\n'.join(i for i in text), reply_markup=admin_kb.admin_kb.as_markup())
    else:
        await callback.message.answer('Список пользователей пуст\nПопробуйте ещё раз', reply_markup=admin_kb.admin_kb.as_markup())

# FSM для создания услуг
@admin_router.callback_query(F.data=='add_service')
async def start_add_service(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer('')
    await state.set_state(ServiceCreation.waiting_for_name)
    await callback.message.answer('Введите название услуги:\n\nДля отмены введите /cancel')

@admin_router.message(ServiceCreation.waiting_for_name)
async def get_service_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(ServiceCreation.waiting_for_description)
    await message.answer('Введите описание услуги:\n\nДля отмены введите /cancel')

@admin_router.message(ServiceCreation.waiting_for_description)
async def get_service_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(ServiceCreation.waiting_for_price)
    await message.answer('Введите цену услуги (в рублях, только число):\n\nДля отмены введите /cancel')

@admin_router.message(ServiceCreation.waiting_for_price)
async def get_service_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        if price <= 0:
            await message.answer('Цена должна быть положительным числом. Попробуйте снова:')
            return
        await state.update_data(price=price)
        await state.set_state(ServiceCreation.waiting_for_duration)
        await message.answer('Введите длительность услуги в минутах (только число):\n\nДля отмены введите /cancel')
    except ValueError:
        await message.answer('Пожалуйста, введите только число для цены:')

@admin_router.message(ServiceCreation.waiting_for_duration)
async def get_service_duration(message: Message, state: FSMContext, session: AsyncSession):
    try:
        duration = int(message.text)
        if duration <= 0:
            await message.answer('Длительность должна быть положительным числом. Попробуйте снова:')
            return
        
        data = await state.get_data()
        new_service = Service(
            name=data['name'],
            description=data['description'],
            price=data['price'],
            duration=duration
        )
        
        session.add(new_service)
        await session.commit()
        
        await state.clear()
        await message.answer(
            f'✅ Услуга успешно добавлена!\n\n'
            f'<b>Название:</b> {data["name"]}\n'
            f'<b>Описание:</b> {data["description"]}\n'
            f'<b>Цена:</b> {data["price"]} ₽\n'
            f'<b>Длительность:</b> {duration} мин.',
            reply_markup=admin_kb.admin_kb.as_markup()
        )
    except ValueError:
        await message.answer('Пожалуйста, введите только число для длительности:')

@admin_router.callback_query(F.data=='view_services')
async def view_services(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('Все услуги')
    
    services = await session.scalars(select(Service).where(Service.is_active == True))
    services_list = list(services)
    
    if services_list:
        text = '<b>Список активных услуг:</b>\n\n'
        for service in services_list:
            service_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text='❌ Удалить услугу', callback_data=f'delete_{service.id}')]
                ]
            )
            text = f'<b>{service.name}</b>\n'
            text += f'📝 {service.description}\n'
            text += f'💰 {service.price} ₽\n'
            text += f'⏱ {service.duration} мин.\n'
            text += f'ID: {service.id}\n\n'
            await callback.message.answer(text, reply_markup=service_kb)
    else:
        await callback.message.answer('Список услуг пуст', reply_markup=admin_kb.back_to_admin.as_markup())
        return
    await callback.message.answer('Выберите услугу для <b>удаления</b> или вернитесь в меню', reply_markup=admin_kb.back_to_admin.as_markup())


@admin_router.callback_query(F.data.startswith('delete_'))
async def delete_service(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.message.delete()
    await callback.message.answer('Вы уверены что хотите удалить услугу?', reply_markup=admin_kb.delete_confirm.as_markup())
    await callback.answer('')
    await state.set_state(DeleteService.waiting_for_confirmation)
    await state.update_data(service_id=callback.data.split('_')[1])



@admin_router.callback_query(F.data=='confirm_delete', DeleteService.waiting_for_confirmation)
async def confirm_delete(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    service_id = data['service_id']
    await session.execute(delete(Service).where(Service.id == service_id))
    await session.commit()
    await state.clear()
    await callback.message.delete()
    await callback.answer('')
    await callback.message.answer(f'Услуга <b>{service_id}</b> успешно удалена', reply_markup=admin_kb.back_to_admin.as_markup())


@admin_router.callback_query(F.data=='view_bookings')
async def view_bookings(callback: CallbackQuery, session: AsyncSession):
    await callback.answer('')
    
    try:
        # Получаем все записи
        bookings = await get_all_bookings(session)
        
        if bookings:
            # Показываем последние 10 записей
            recent_bookings = bookings[:10]
            
            for booking in recent_bookings:
                booking_text = f"<b>Запись #{booking.id}</b>\n"
                booking_text += f"👤 <b>Клиент:</b> {booking.client_name}\n"
                booking_text += f"📞 <b>Телефон:</b> {booking.phone}\n"
                booking_text += f"🎯 <b>Услуга:</b> {booking.service.name}\n"
                booking_text += f"💰 <b>Стоимость:</b> {booking.service.price} ₽\n"
                booking_text += f"📅 <b>Дата:</b> {booking.preferred_date}\n"
                booking_text += f"🕐 <b>Время:</b> {booking.preferred_time}\n"
                booking_text += f"📝 <b>Создана:</b> {booking.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                
                await callback.message.answer(
                    booking_text, 
                    reply_markup=admin_kb.get_booking_actions_kb(booking.id)
                )
                
            # Информация о количестве записей
            if len(bookings) > 10:
                await callback.message.answer(
                    f"📊 <b>Показано последних 10 записей из {len(bookings)}</b>\n\n"
                    f"Для просмотра следующих записей удалите старые.",
                    reply_markup=admin_kb.back_to_admin.as_markup()
                )
            else:
                await callback.message.answer(
                    f"📊 <b>Показано {len(bookings)} записей</b>\n\n"
                    f"Если вы уже поработали или встреча не состоялась\n"
                    f"<b>Завершите</b> либо <b>Отмените</b> запись\n\n"
                    f"<b>При завершении</b> клиенту придет уведомление с просьбой об отзыве\n"
                    f"<b>При отмене</b> пользователю придет уведомление об отмене его записи",
                    reply_markup=admin_kb.back_to_admin.as_markup()
                )

        else:
            await callback.message.answer(
                '📋 Записей пока нет', 
                reply_markup=admin_kb.admin_kb.as_markup()
            )
    except Exception as e:
        print(f"Ошибка при получении записей: {e}")
        await callback.message.answer(
            '❌ Произошла ошибка при получении записей', 
            reply_markup=admin_kb.admin_kb.as_markup()
        )


@admin_router.callback_query(F.data.startswith('booking_cancel_'))
async def cancel_booking(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    booking_id = callback.data.split('_')[2]
    booking_user_chat = await delete_booking(session, booking_id)
    if booking_user_chat:
        await bot.send_message(chat_id=booking_user_chat, text='Ваша запись отменена ❌')
        await callback.message.answer(f'Запись <b>{booking_id}</b> отменена и удалена', reply_markup=admin_kb.back_to_admin.as_markup())
    else:
        await callback.message.answer(f'Запись <b>{booking_id}</b> не найдена', reply_markup=admin_kb.back_to_admin.as_markup())
    await callback.message.delete()
    await callback.answer('')
    

@admin_router.callback_query(F.data.startswith('booking_complete_'))
async def complete_booking(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    booking_id = callback.data.split('_')[2]
    booking_user_chat = await delete_booking(session, booking_id)
    if booking_user_chat:
        await bot.send_message(chat_id=booking_user_chat, text='Прошу вас оставить отзыв о моей работе!', reply_markup=admin_kb.review_kb)    
        await callback.message.answer(f'Запись <b>{booking_id}</b> завершена и удалена', reply_markup=admin_kb.back_to_admin.as_markup())
    else:
        await callback.message.answer(f'Запись <b>{booking_id}</b> не найдена', reply_markup=admin_kb.back_to_admin.as_markup())
    await callback.message.delete()
    await callback.answer('')
    