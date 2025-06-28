from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

import keyboards.funnel_kb as funnel_kb
import filters.admin_filter as Admin
from database.models import Funnel, FunnelStep
from database.orm_query import get_active_funnels, get_funnel_with_steps, create_funnel, create_funnel_step, delete_funnel

class FunnelCreation(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()

class FunnelStepCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_delay = State()
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
            f'Теперь добавьте этапы в воронку.',
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
            # Получаем количество этапов
            funnel_with_steps = await get_funnel_with_steps(session, funnel.id)
            steps_count = len(funnel_with_steps.steps)

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
async def start_add_funnel_step(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer('')
    await state.set_state(FunnelStepCreation.waiting_for_title)
    await callback.message.answer(
        '📝 <b>Добавление этапа воронки</b>\n\n'
        'Введите заголовок этапа:\n\n'
        '<i>Например: "День 1: Основы дыхательной гимнастики"</i>\n\n'
        'Для отмены введите /cancel'
    )

@funnel_admin_router.message(F.text, FunnelStepCreation.waiting_for_title)
async def get_step_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(FunnelStepCreation.waiting_for_content)
    await message.answer(
        '📄 Введите контент этапа:\n\n'
        '<i>Текст или видео, который получит пользователь</i>\n\n'
        'Для отмены введите /cancel'
    )

@funnel_admin_router.message(F.text, FunnelStepCreation.waiting_for_content)
async def get_step_content(message: Message, state: FSMContext, session: AsyncSession):

    # Для текста сохраняем текст
    await state.update_data(content=message.text)
    await state.update_data(content_type='text')
    await state.update_data(file_id=None)
    
    await state.set_state(FunnelStepCreation.waiting_for_delay)
    await message.answer(
        '⏰ Введите задержку перед отправкой (в часах):\n\n'
        '<i>0 - отправить сразу, 24 - через сутки</i>\n\n'
        'Для отмены введите /cancel'
    )

@funnel_admin_router.message(F.text, FunnelStepCreation.waiting_for_delay)
async def get_step_delay(message: Message, state: FSMContext):
    try:
        delay = int(message.text)
        if delay < 0:
            await message.answer('❌ Задержка не может быть отрицательной. Попробуйте снова:')
            return
    except ValueError:
        await message.answer('❌ Пожалуйста, введите число. Попробуйте снова:')
        return
    
    await state.update_data(delay_hours=delay)
    await state.set_state(FunnelStepCreation.waiting_for_step_type)
    await message.answer(
        '💰 Выберите тип этапа:\n\n'
        '🆓 <b>Бесплатный</b> - пользователь получает сразу\n'
        '💰 <b>Платный</b> - предлагается записаться на консультацию\n\n'
        'Выберите "бесплатный" или "платный":', reply_markup=funnel_kb.free_paid_kb
    )

@funnel_admin_router.message(F.video, FunnelStepCreation.waiting_for_content)
async def get_step_video(message: Message, state: FSMContext, session: AsyncSession):
    # Для видео сохраняем file_id и добавляем описание
    await state.update_data(file_id=message.video.file_id)
    await state.update_data(content_type='video')
    await state.update_data(content=message.caption or "Видео урок")
    
    await state.set_state(FunnelStepCreation.waiting_for_delay)
    await message.answer(
        '⏰ Введите задержку перед отправкой (в часах):\n\n'
        '<i>0 - отправить сразу, 24 - через сутки</i>\n\n'
        'Для отмены введите /cancel'
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
        funnels = await get_active_funnels(session)
        if not funnels:
            await message.answer('❌ Нет активных воронок. Сначала создайте воронку.')
            await state.clear()
            return
        
        funnel = funnels[0]

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
            delay_hours=data['delay_hours'],
            is_free=is_free,
            file_id=data.get('file_id')
        )

        await state.clear()
        content_type_text = "Видео" if data['content_type'] == 'video' else "Текст"
        await message.answer(
            f'✅ <b>Этап успешно добавлен!</b>\n\n'
            f'📝 <b>Заголовок:</b> {data["title"]}\n'
            f'📄 <b>Тип контента:</b> {content_type_text}\n'
            f'⏰ <b>Задержка:</b> {data["delay_hours"]} ч.\n'
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
    
    funnel = funnels[0]
    funnel_with_steps = await get_funnel_with_steps(session, funnel.id)

    if funnel_with_steps.steps:
        text = f'📋 <b>Этапы воронки "{funnel.name}"</b>\n\n'
        for step in funnel_with_steps.steps:
            content_type_icon = "🎥" if step.content_type == 'video' else "📝"
            text += f'{content_type_icon} <b>{step.order}. {step.title}</b>\n'
            text += f'📄 Тип контента: {"Видео" if step.content_type == "video" else "Текст"}\n'
            text += f'⏰ Задержка: {step.delay_hours} ч.\n'
            text += f'💰 Тип: {"Бесплатный" if step.is_free else "Платный"}\n\n'
        
        await callback.message.answer(text, reply_markup=funnel_kb.funnel_manage_kb.as_markup())
    else:
        await callback.message.answer(
            '📭 Этапы воронки не найдены\n\nДобавьте первый этап!',
            reply_markup=funnel_kb.funnel_manage_kb.as_markup()
        )

# Удаление воронки
@funnel_admin_router.callback_query(F.data=='delete_funnel')
async def confirm_delete_funnel(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer('')
    await callback.message.answer(
        '⚠️ <b>Внимание!</b>\n\n'
        'Вы уверены, что хотите удалить воронку?\n'
        'Это действие нельзя отменить.',
        reply_markup=funnel_kb.delete_funnel_confirm
    )

@funnel_admin_router.callback_query(F.data=='confirm_delete_funnel')
async def delete_funnel_action(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    
    try:
        # Получаем активную воронку
        funnels = await get_active_funnels(session)
        if not funnels:
            await callback.message.answer('❌ Нет активных воронок.')
            return

        funnel = funnels[0]
        await delete_funnel(session, funnel.id)

        await callback.message.answer(
            f'✅ Воронка "{funnel.name}" успешно удалена!',
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