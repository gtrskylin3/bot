from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, and_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import keyboards.admin_kb as admin_kb
import filters.admin_filter as Admin
from database.models import User, Service
from database.orm_query import get_active_users, deactivate_user, get_or_create_broadcast_settings, update_default_broadcast_text


class ServiceCreation(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_duration = State()


class BroadcastSettings(StatesGroup):
    waiting_for_default_text = State()
    waiting_for_custom_text = State()


admin_router = Router()
admin_router.message.filter(Admin.IsAdmin())

@admin_router.message(CommandStart())
async def admin_start(message: Message):
    await message.answer('Вы админисктратор вы можете cделать:', reply_markup=admin_kb.admin_kb.as_markup())

@admin_router.callback_query(F.data=='send_all')
async def send_all_menu(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    
    # Получаем настройки рассылки админа
    settings = await get_or_create_broadcast_settings(session)
    

    
    
    await callback.message.answer(
        f'📢 <b>Настройка рассылки</b>\n\n'
        f'Текущий стандартный текст:\n'
        f'<i>"{settings.default_text}"</i>\n\n'
        f'Выберите тип рассылки:',
        reply_markup=admin_kb.broadcast_kb.as_markup()
    )

@admin_router.callback_query(F.data=='send_default')
async def send_default_broadcast(callback: CallbackQuery, bot: Bot, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    
    # Получаем стандартный текст
    settings = await get_or_create_broadcast_settings(session)
    users = await get_active_users(session)
    
    if users:
        success_count = 0
        failed_count = 0
        
        for user in users:
            try:
                await bot.send_message(chat_id=str(user.tg_id), text=settings.default_text)
                success_count += 1
            except Exception as e:
                failed_count += 1
                await deactivate_user(session, user.tg_id)
                print(f"Ошибка отправки пользователю {user.tg_id}: {e}")
        
        await callback.message.answer(
            f"✅ Рассылка стандартным текстом завершена!\n\n"
            f"📤 Отправлено: {success_count}\n"
            f"❌ Ошибок: {failed_count}\n\n"
            f"📝 Текст: <i>\"{settings.default_text}\"</i>",
            reply_markup=admin_kb.admin_kb.as_markup()
        )
    else:
        await callback.message.answer('Список пользователей пуст', reply_markup=admin_kb.admin_kb.as_markup())

@admin_router.callback_query(F.data=='send_custom')
async def start_custom_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer('')
    await state.set_state(BroadcastSettings.waiting_for_custom_text)
    await callback.message.answer(
        '✏️ Введите текст для рассылки:\n\n'
        'Для отмены введите /cancel'
    )

@admin_router.callback_query(F.data=='change_default')
async def start_change_default(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer('')
    await state.set_state(BroadcastSettings.waiting_for_default_text)
    await callback.message.answer(
        '⚙️ Введите новый стандартный текст для рассылки:\n\n'
        'Для отмены введите /cancel'
    )

@admin_router.callback_query(F.data=='back_to_admin')
async def back_to_admin(callback: CallbackQuery):
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

@admin_router.message(BroadcastSettings.waiting_for_custom_text)
async def get_custom_text(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    custom_text = message.text
    await state.clear()
    
    # Получаем активных пользователей
    users = await get_active_users(session)
    
    if users:
        success_count = 0
        failed_count = 0
        
        for user in users:
            try:
                await bot.send_message(chat_id=str(user.tg_id), text=custom_text)
                success_count += 1
            except Exception as e:
                # Если пользователь заблокировал бота или другая ошибка
                failed_count += 1
                await deactivate_user(session, user.tg_id)
                print(f"Ошибка отправки пользователю {user.tg_id}: {e}")
        
        await message.answer(
            f"✅ Рассылка кастомным текстом завершена!\n\n"
            f"📤 Отправлено: {success_count}\n"
            f"❌ Ошибок: {failed_count}\n\n"
            f"📝 Текст: <i>\"{custom_text}\"</i>",
            reply_markup=admin_kb.admin_kb.as_markup()
        )
    else:
        await message.answer('Список пользователей пуст', reply_markup=admin_kb.admin_kb.as_markup())

@admin_router.message(BroadcastSettings.waiting_for_default_text)
async def get_new_default_text(message: Message, state: FSMContext, session: AsyncSession):
    new_text = message.text
    await state.clear()
    
    # Обновляем стандартный текст
    await update_default_broadcast_text(session, new_text)
    
    await message.answer(
        f"✅ Стандартный текст обновлен!\n\n"
        f"📝 Новый текст: <i>\"{new_text}\"</i>\n\n"
        f"Теперь при выборе 'Стандартный текст' будет отправляться этот текст.",
        reply_markup=admin_kb.admin_kb.as_markup()
    )

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
    await callback.answer('')
    
    services = await session.scalars(select(Service).where(Service.is_active == True))
    services_list = list(services)
    
    if services_list:
        text = '<b>Список активных услуг:</b>\n\n'
        for service in services_list:
            text += f'<b>{service.name}</b>\n'
            text += f'📝 {service.description}\n'
            text += f'💰 {service.price} ₽\n'
            text += f'⏱ {service.duration} мин.\n'
            text += f'ID: {service.id}\n\n'
    else:
        text = 'Список услуг пуст'
    
    await callback.message.answer(text, reply_markup=admin_kb.admin_kb.as_markup())

