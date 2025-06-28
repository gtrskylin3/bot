from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

import keyboards.funnel_kb as funnel_kb
import filters.admin_filter as Admin
from database.models import Funnel, FunnelStep, FunnelProgress
from database.orm_query import (
    get_active_funnels, 
    get_funnel_with_steps, 
    create_funnel, 
    create_funnel_step, 
    delete_funnel
)

class FunnelCreation(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()

class FunnelStepCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_step_type = State()

# Создаем роутер и применяем фильтр админа
funnel_admin_router = Router()
funnel_admin_router.message.filter(Admin.IsAdmin())
funnel_admin_router.callback_query.filter(Admin.IsAdmin())

# Обработчик для входа в управление воронками
@funnel_admin_router.callback_query(F.data == 'manage_funnels')
async def manage_funnels(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer('')
    await callback.message.answer(
        '🔄 <b>Управление воронками продаж</b>\n\n'
        'Здесь вы можете создавать и управлять воронками для привлечения клиентов.',
        reply_markup=funnel_kb.admin_funnel_kb.as_markup()
    )

@funnel_admin_router.callback_query(F.data == 'create_funnel')
async def start_create_funnel(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer('')
    await state.set_state(FunnelCreation.waiting_for_name)
    await callback.message.answer(
        '🆕 <b>Создание новой воронки</b>\n\n'
        'Введите название воронки:\n\n'
        '<i>Например: "Курс по снятию стресса"</i>\n\n'
        'Для отмены введите /cancel'
    )

@funnel_admin_router.message(F.text, FunnelCreation.waiting_for_name)
async def get_funnel_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(FunnelCreation.waiting_for_description)
    await message.answer(
        '📝 Введите описание воронки:\n\n'
        '<i>Краткое описание того, что получит пользователь</i>\n\n'
        'Для отмены введите /cancel'
    )
    
@funnel_admin_router.message(F.text, FunnelCreation.waiting_for_description)
async def get_funnel_description(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()

    try: 
        funnel = await create_funnel(
            session=session, 
            name=data['name'], 
            description=message.text
        )
        await state.clear()
        await message.answer(
            f'✅ <b>Воронка успешно создана!</b>\n\n'
            f'📋 <b>Название:</b> {data["name"]}\n'
            f'📝 <b>Описание:</b> {message.text}\n'
            f'🆔 <b>ID воронки:</b> {funnel.id}\n\n'
            'Теперь добавьте этапы в воронку.',
            reply_markup=funnel_kb.funnel_manage_kb.as_markup()
        )
        # Сохраняем ID воронки для добавления этапов
        await state.update_data(current_funnel_id=funnel.id)
    except Exception as e:
        await message.answer(
            f'❌ Произошла ошибка при создании воронки:\n\n'
            f'<code>{str(e)}</code>\n\n'
            'Пожалуйста, попробуйте снова.',
            reply_markup=funnel_kb.admin_funnel_kb.as_markup()
        )
        await state.clear()

# Список воронок
@funnel_admin_router.callback_query(F.data == 'list_funnels')
async def list_funnels(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    funnels = await get_active_funnels(session)
    if funnels:
        for funnel in funnels:
            # Получаем количество этапов для конкретной воронки
            funnel_with_steps = await get_funnel_with_steps(session, funnel.id)
            steps_count = len(funnel_with_steps.steps) if funnel_with_steps else 0

            text = f'📋 <b>{funnel.name}</b>\n\n'
            if funnel.description:
                text += f'📄 {funnel.description}\n\n'
            text += f'🆔 <b>ID:</b> {funnel.id}\n'
            text += f'📊 <b>Этапов:</b> {steps_count}\n'
            text += f'📅 <b>Создана:</b> {funnel.created_at.strftime("%d.%m.%Y")}\n'

            # Кнопка управления воронкой
            manage_kb = funnel_kb.funnel_manage_kb.as_markup()
            await callback.message.answer(text, reply_markup=manage_kb)
    else:
        await callback.message.answer(
            '📭 Список воронок пуст\n\nСоздайте первую воронку!',
            reply_markup=funnel_kb.admin_funnel_kb.as_markup()
        )

# Добавление этапа воронки
@funnel_admin_router.callback_query(F.data=='add_funnel_step')
async def start_add_funnel_step(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    
    # Получаем список воронок для выбора
    funnels = await get_active_funnels(session)
    if not funnels:
        await callback.message.answer(
            '❌ Нет активных воронок. Сначала создайте воронку.',
            reply_markup=funnel_kb.admin_funnel_kb.as_markup()
        )
        return
    
    await callback.message.answer(
        '📋 Выберите воронку для добавления этапа:',
        reply_markup=funnel_kb.get_funnel_selection_kb(funnels)
    )

@funnel_admin_router.callback_query(F.data.startswith('select_funnel:'))
async def select_funnel_for_step(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    
    try:
        # Извлекаем ID воронки из callback_data
        funnel_id = int(callback.data.split(':')[1])
        funnel = await session.get(Funnel, funnel_id)
        
        if funnel and funnel.is_active:
            await state.update_data(selected_funnel_id=funnel_id)
            
            await state.set_state(FunnelStepCreation.waiting_for_title)
            await callback.message.answer(
                '📝 <b>Добавление этапа воронки</b>\n\n'
                'Введите заголовок этапа:\n\n'
                '<i>Например: "День 1: Основы дыхательной гимнастики"</i>\n\n'
                'Для отмены введите /cancel'
            )
        else:
            await callback.message.answer('❌ Воронка не найдена или неактивна.')
    except (ValueError, IndexError):
        await callback.message.answer('❌ Ошибка при выборе воронки.')

@funnel_admin_router.callback_query(F.data.startswith('view_funnel:'))
async def select_funnel_for_view(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    
    try:
        # Извлекаем ID воронки из callback_data
        funnel_id = int(callback.data.split(':')[1])
        funnel = await session.get(Funnel, funnel_id)
        
        if funnel and funnel.is_active:
            await show_funnel_steps_for_funnel(callback.message, session, funnel)
        else:
            await callback.message.answer('❌ Воронка не найдена или неактивна.')
    except (ValueError, IndexError):
        await callback.message.answer('❌ Ошибка при выборе воронки.')

@funnel_admin_router.callback_query(F.data.startswith('stats_funnel:'))
async def select_funnel_for_stats(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    
    try:
        # Извлекаем ID воронки из callback_data
        funnel_id = int(callback.data.split(':')[1])
        funnel = await session.get(Funnel, funnel_id)
        
        if funnel and funnel.is_active:
            await show_funnel_stats_for_funnel(callback.message, session, funnel)
        else:
            await callback.message.answer('❌ Воронка не найдена или неактивна.')
    except (ValueError, IndexError):
        await callback.message.answer('❌ Ошибка при выборе воронки.')

@funnel_admin_router.message(F.text, FunnelStepCreation.waiting_for_title)
async def get_step_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(FunnelStepCreation.waiting_for_content)
    await message.answer(
        '📄 Введите контент этапа:\n\n'
        '<i>Отправьте текст или видео, который получит пользователь</i>\n\n'
        'Для отмены введите /cancel'
    )

@funnel_admin_router.message(F.text, FunnelStepCreation.waiting_for_content)
async def get_step_content(message: Message, state: FSMContext, session: AsyncSession):
    # Для текста сохраняем текст
    await state.update_data(content=message.text)
    await state.update_data(content_type='text')
    await state.update_data(file_id=None)
    
    await state.set_state(FunnelStepCreation.waiting_for_step_type)
    await message.answer(
        '💰 Выберите тип этапа:\n\n'
        '🆓 <b>Бесплатный</b> - пользователь получает сразу\n'
        '💰 <b>Платный</b> - предлагается записаться на консультацию\n\n'
        'Выберите "бесплатный" или "платный":', reply_markup=funnel_kb.free_paid_kb
    )

@funnel_admin_router.message(F.video, FunnelStepCreation.waiting_for_content)
async def get_step_video(message: Message, state: FSMContext):
    # Для видео сохраняем file_id и добавляем описание
    await state.update_data(file_id=message.video.file_id)
    await state.update_data(content_type='video')
    await state.update_data(content=message.caption or "Видео урок")
    
    await state.set_state(FunnelStepCreation.waiting_for_step_type)
    await message.answer(
        '💰 Выберите тип этапа:\n\n'
        '🆓 <b>Бесплатный</b> - пользователь получает сразу\n'
        '💰 <b>Платный</b> - предлагается записаться на консультацию\n\n'
        'Выберите "бесплатный" или "платный":', reply_markup=funnel_kb.free_paid_kb
    )

@funnel_admin_router.message(F.text, FunnelStepCreation.waiting_for_step_type)
async def get_step_type(message: Message, state: FSMContext, session: AsyncSession):
    step_type = message.text.lower().strip()

    if step_type not in ['бесплатный', 'платный']:
        await message.answer('❌ Пожалуйста, введите "бесплатный" или "платный"', reply_markup=funnel_kb.free_paid_kb)
        return
    
    is_free = step_type == 'бесплатный'
    data = await state.get_data()

    try: 
        # Используем выбранную воронку из state
        selected_funnel_id = data.get('selected_funnel_id')
        if not selected_funnel_id:
            await message.answer('❌ Ошибка: воронка не выбрана.')
            await state.clear()
            return
        
        # Получаем выбранную воронку
        funnel = await session.get(Funnel, selected_funnel_id)
        if not funnel:
            await message.answer('❌ Воронка не найдена.')
            await state.clear()
            return

        # Получаем порядковый номер этапа
        funnel_with_steps = await get_funnel_with_steps(session, funnel.id)
        next_order = len(funnel_with_steps.steps) + 1

        # Создаем этап
        step = await create_funnel_step(
            session=session,
            funnel_id=funnel.id,
            order=next_order,
            title=data['title'],
            content=data['content'],
            content_type=data['content_type'],
            is_free=is_free,
            file_id=data.get('file_id')
        )

        await state.clear()
        content_type_text = "Видео" if data['content_type'] == 'video' else "Текст"
        await message.answer(
            f'✅ <b>Этап успешно добавлен в воронку "{funnel.name}"!</b>\n\n'
            f'📝 <b>Заголовок:</b> {data["title"]}\n'
            f'📄 <b>Тип контента:</b> {content_type_text}\n'
            f'💰 <b>Тип:</b> {"Бесплатный" if is_free else "Платный"}\n'
            f'🆔 <b>ID этапа:</b> {step.id}',
            reply_markup=funnel_kb.funnel_manage_kb.as_markup()
        )
    except Exception as e:
        await message.answer(
            f'❌ Ошибка при создании этапа: {e}',
            reply_markup=funnel_kb.admin_funnel_kb.as_markup()
        )

# Просмотр этапов воронки
@funnel_admin_router.callback_query(F.data=='view_funnel_steps')
async def view_funnel_steps(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    
    funnels = await get_active_funnels(session)
    if not funnels:
        await callback.message.answer('❌ Нет активных воронок.')
        return
    
    # Если воронка одна, показываем её этапы
    if len(funnels) == 1:
        funnel = funnels[0]
        await show_funnel_steps_for_funnel(callback.message, session, funnel)
    else:
        # Если воронок несколько, предлагаем выбрать
        await callback.message.answer(
            '📋 Выберите воронку для просмотра этапов:',
            reply_markup=funnel_kb.get_funnel_selection_kb(funnels, 'view_funnel')
        )

async def show_funnel_steps_for_funnel(message: Message, session: AsyncSession, funnel: Funnel):
    """Показывает этапы конкретной воронки"""
    funnel_with_steps = await get_funnel_with_steps(session, funnel.id)

    if funnel_with_steps and funnel_with_steps.steps:
        text = f'📋 <b>Этапы воронки "{funnel.name}"</b>\n\n'
        for step in funnel_with_steps.steps:
            content_type_icon = "🎥" if step.content_type == 'video' else "📝"
            text += f'{content_type_icon} <b>{step.order}. {step.title}</b>\n'
            text += f'📄 Тип контента: {"Видео" if step.content_type == "video" else "Текст"}\n'
            text += f'💰 Тип: {"Бесплатный" if step.is_free else "Платный"}\n\n'
        
        await message.answer(text, reply_markup=funnel_kb.funnel_manage_kb.as_markup())
    else:
        await message.answer(
            f'📭 Этапы воронки "{funnel.name}" не найдены\n\nДобавьте первый этап!',
            reply_markup=funnel_kb.funnel_manage_kb.as_markup()
        )

# Статистика воронки
@funnel_admin_router.callback_query(F.data == 'funnel_stats')
async def show_funnel_stats(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    
    funnels = await get_active_funnels(session)
    if not funnels:
        await callback.message.answer('❌ Нет активных воронок.')
        return
    
    # Если воронка одна, показываем её статистику
    if len(funnels) == 1:
        funnel = funnels[0]
        await show_funnel_stats_for_funnel(callback.message, session, funnel)
    else:
        # Если воронок несколько, предлагаем выбрать
        await callback.message.answer(
            '📋 Выберите воронку для просмотра статистики:',
            reply_markup=funnel_kb.get_funnel_selection_kb(funnels, 'stats_funnel')
        )

async def show_funnel_stats_for_funnel(message: Message, session: AsyncSession, funnel: Funnel):
    """Показывает статистику конкретной воронки"""
    # Получаем статистику
    # Общее количество участников
    total_users = await session.scalar(
        select(func.count(FunnelProgress.id))
        .where(FunnelProgress.funnel_id == funnel.id)
    )
    
    # Завершивших курс
    completed_users = await session.scalar(
        select(func.count(FunnelProgress.id))
        .where(FunnelProgress.funnel_id == funnel.id)
        .where(FunnelProgress.is_completed == True)
    )
    
    # Активных участников (не завершивших)
    active_users = total_users - completed_users if total_users else 0
    
    # Конверсия
    conversion = (completed_users / total_users * 100) if total_users > 0 else 0
    
    stats_text = f'📊 <b>Статистика воронки "{funnel.name}"</b>\n\n'
    stats_text += f'👥 <b>Всего участников:</b> {total_users}\n'
    stats_text += f'✅ <b>Завершили курс:</b> {completed_users}\n'
    stats_text += f'🔄 <b>В процессе:</b> {active_users}\n'
    stats_text += f'📈 <b>Конверсия:</b> {conversion:.1f}%\n'
    
    await message.answer(stats_text, reply_markup=funnel_kb.admin_funnel_kb.as_markup())

# Настройки воронки
@funnel_admin_router.callback_query(F.data == 'funnel_settings')
async def show_funnel_settings(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    
    funnels = await get_active_funnels(session)
    if not funnels:
        await callback.message.answer('❌ Нет активных воронок.')
        return
    
    funnel = funnels[0]
    
    settings_text = f'⚙️ <b>Настройки воронки "{funnel.name}"</b>\n\n'
    settings_text += f'📋 <b>Название:</b> {funnel.name}\n'
    settings_text += f'📝 <b>Описание:</b> {funnel.description}\n'
    settings_text += f'🆔 <b>ID:</b> {funnel.id}\n'
    settings_text += f'📅 <b>Создана:</b> {funnel.created_at.strftime("%d.%m.%Y")}\n'
    settings_text += f'🔄 <b>Статус:</b> {"Активна" if funnel.is_active else "Неактивна"}\n\n'
    settings_text += '🔧 <i>Функция редактирования настроек будет добавлена позже</i>'
    
    await callback.message.answer(settings_text, reply_markup=funnel_kb.funnel_manage_kb.as_markup())

# Удаление воронки
@funnel_admin_router.callback_query(F.data=='delete_funnel')
async def confirm_delete_funnel(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer('')
    await callback.message.answer(
        '⚠️ <b>Подтверждение удаления</b>\n\n'
        'Вы уверены, что хотите удалить воронку?\n\n'
        '<b>Это действие нельзя отменить!</b>',
        reply_markup=funnel_kb.delete_funnel_confirm
    )

@funnel_admin_router.callback_query(F.data=='confirm_delete_funnel')
async def delete_funnel_action(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    
    funnels = await get_active_funnels(session)
    if not funnels:
        await callback.message.answer('❌ Нет активных воронок.')
        return
    
    funnel = funnels[0]
    
    try:
        await delete_funnel(session, funnel.id)
        await callback.message.answer(
            f'✅ <b>Воронка "{funnel.name}" успешно удалена!</b>\n\n'
            'Все этапы и прогресс пользователей также удалены.',
            reply_markup=funnel_kb.admin_funnel_kb.as_markup()
        )
    except Exception as e:
        await callback.message.answer(
            f'❌ Ошибка при удалении воронки: {e}',
            reply_markup=funnel_kb.admin_funnel_kb.as_markup()
        )

# Отмена операций
@funnel_admin_router.message(Command('cancel'))
async def cancel_funnel_operation(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer(
            '❌ Операция отменена.',
            reply_markup=funnel_kb.admin_funnel_kb.as_markup()
        )
    else:
        await message.answer('Нет активной операции для отмены.') 