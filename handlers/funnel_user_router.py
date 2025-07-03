from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext
from datetime import datetime

import keyboards.funnel_kb as funnel_kb
import keyboards.user_kb as user_kb
from database.orm_query import (
    get_active_funnels, 
    start_user_funnel, 
    get_user_funnel_progress, 
    get_funnel_with_steps, 
    advance_user_funnel,
    reset_user_funnel_progress,
    get_user_all_funnel_progress
)
from database.models import FunnelProgress, Funnel

# Создаем роутер для пользователей в воронке
funnel_user_router = Router()

# Функция для отправки этапа воронки
async def send_funnel_step(message: Message, session: AsyncSession, progress: FunnelProgress, funnel: Funnel):
    """Отправляет этап воронки пользователю"""
    funnel_with_steps = await get_funnel_with_steps(session, funnel.id)
    
    # Проверяем, есть ли этапы в воронке
    if not funnel_with_steps or not funnel_with_steps.steps:
        await message.answer(
            '❌ Курс еще не готов. Попробуйте позже.',
            reply_markup=user_kb.back_mrk
        )
        return
    
    total_steps = len(funnel_with_steps.steps)

    # НОВАЯ ПРОВЕРКА: Если курс помечен как завершенный, но этапов стало больше
    if progress.is_completed and progress.current_step < total_steps:
        # Проверяем, есть ли бесплатные этапы после текущего
        has_free_steps_ahead = False
        for i in range(progress.current_step - 1, total_steps):  # -1 потому что индексация с 0
            step = funnel_with_steps.steps[i]
            if step.is_free:
                has_free_steps_ahead = True
                break
        
        # Если есть бесплатные этапы впереди, снимаем флаг завершения
        if has_free_steps_ahead:
            progress.is_completed = False
            progress.completed_at = None
            await session.commit()

    # Проверяем, что текущий этап существует
    if progress.current_step > len(funnel_with_steps.steps) or progress.current_step < 1:
        await message.answer('❌ Этап не найден')
        return
    
    current_step = funnel_with_steps.steps[progress.current_step - 1]
    
    
    # Формируем текст сообщения
    step_text = f'📚 <b>{current_step.title}</b>\n\n'
    step_text += f'{current_step.content}\n\n'
    
    # Определяем клавиатуру в зависимости от типа этапа
    if current_step.is_free:
        # Бесплатный этап
        if progress.current_step == total_steps:
            # Это последний этап - курс завершен
            progress.is_completed = True
            progress.completed_at = datetime.now()
            await session.commit()
            
            step_text += '🎉 <b>Поздравляем! Вы завершили курс!</b>\n\n'
            step_text += 'Теперь вы можете записаться на индивидуальную консультацию.'
            reply_markup = funnel_kb.funnel_complete_kb
        else:
            # Показываем кнопку "Следующий урок"
            reply_markup = funnel_kb.funnel_next_kb
    else:
        # Платный этап - курс завершен на платной части
        progress.is_completed = True
        progress.completed_at = datetime.now()
        await session.commit()
        
        step_text += '💰 <b>Это платный этап курса</b>\n\n'
        step_text += 'Для продолжения обучения запишитесь к психологу.\n\n'
        step_text += '📞 <b>Свяжитесь с психологом:</b> @Olesja_Chernova'
        reply_markup = funnel_kb.funnel_paid_stop_kb
    
    # Отправляем контент в зависимости от типа
    if current_step.content_type == 'video' and current_step.file_id:
        # Отправляем видео с подписью
        await message.answer_video(
            video=current_step.file_id,
            caption=step_text,
            reply_markup=reply_markup
        )
    else:
        # Отправляем только текст
        await message.answer(step_text, reply_markup=reply_markup)

# Показ списка доступных курсов
@funnel_user_router.callback_query(F.data=='start_funnel')
async def show_available_courses(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer('')
    
    funnels = await get_active_funnels(session)
    if not funnels:
        await callback.message.answer(
            '❌ В данный момент нет доступных курсов.\nПопробуйте позже!',
            reply_markup=user_kb.back_mrk
        )
        return
    
    # Если курс один, сразу начинаем его
    if len(funnels) == 1:
        funnel = funnels[0]
        await start_course_for_user(callback.message, session, funnel, state)
    else:
        # Если курсов несколько, показываем выбор
        await show_course_selection(callback.message, funnels)

async def show_course_selection(message: Message, funnels: list[Funnel]):
    """Показывает список курсов для выбора"""
    text = '📚 <b>Доступные курсы</b>\n\n'
    text += 'Выберите курс, который хотите пройти:\n\n'
    
    # Создаем клавиатуру с курсами
    kb = funnel_kb.get_course_selection_kb(funnels)
    
    await message.answer(text, reply_markup=kb)

async def start_course_for_user(message: Message, session: AsyncSession, funnel: Funnel, state: FSMContext = None):
    """Начинает курс для пользователя"""
    # Получаем или создаем прогресс пользователя
    progress = await start_user_funnel(session, message.chat.id, funnel.id)
    
    # Сохраняем ID воронки в state для правильной работы
    if state is not None:
        await state.update_data(current_funnel_id=funnel.id)
    
    # Отправляем первый этап
    await send_funnel_step(message, session, progress, funnel)

# Обработчик выбора конкретного курса
@funnel_user_router.callback_query(F.data.startswith('select_course:'))
async def select_course_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer('')
    
    try:
        # Извлекаем ID курса из callback_data
        funnel_id = int(callback.data.split(':')[1])
        funnel = await session.get(Funnel, funnel_id)
        
        if funnel and funnel.is_active:
            await start_course_for_user(callback.message, session, funnel, state)
        else:
            await callback.message.answer('❌ Курс не найден или неактивен.')
    except (ValueError, IndexError):
        await callback.message.answer('❌ Ошибка при выборе курса.')

# Переход к следующему этапу воронки
@funnel_user_router.callback_query(F.data=='funnel_next')
async def next_funnel_step(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer('')
    
    # Получаем ID текущей воронки из state
    data = await state.get_data()
    current_funnel_id = data.get('current_funnel_id')
    
    if not current_funnel_id:
        await callback.message.answer('❌ Курс не найден. Начните курс заново.')
        return
    
    # Получаем текущую воронку
    current_funnel = await session.get(Funnel, current_funnel_id)
    if not current_funnel:
        await callback.message.answer('❌ Курс не найден. Начните курс заново.')
        return
    
    # Получаем прогресс пользователя по конкретной воронке
    user_progress = await get_user_funnel_progress(session, callback.from_user.id, current_funnel_id)
    
    if not user_progress:
        await callback.message.answer('❌ Прогресс не найден. Начните курс заново.')
        return
    
    # Проверяем, завершен ли курс
    # if user_progress.is_completed:
    #     await callback.message.answer(
    #         '🎉 <b>Поздравляем! Вы завершили курс!</b>\n\n'
    #         'Теперь вы можете записаться на индивидуальную консультацию.',
    #         reply_markup=funnel_kb.funnel_complete_kb
    #     )
    #     return
    
    # Переходим к следующему этапу
    updated_progress = await advance_user_funnel(session, callback.from_user.id, current_funnel_id)
    
    if updated_progress:
        # Отправляем следующий этап (логика завершения обрабатывается в send_funnel_step)
        await send_funnel_step(callback.message, session, updated_progress, current_funnel)
    else:
        await callback.message.answer('❌ Ошибка при переходе к следующему этапу.')

# Показ прогресса пользователя
@funnel_user_router.callback_query(F.data=='funnel_progress')
async def show_funnel_progress(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer('')
    
    # Получаем ID текущей воронки из state
    data = await state.get_data()
    current_funnel_id = data.get('current_funnel_id')
    
    if not current_funnel_id:
        await callback.message.answer('❌ Курс не найден. Начните курс заново.')
        return
    
    # Получаем текущую воронку
    current_funnel = await session.get(Funnel, current_funnel_id)
    if not current_funnel:
        await callback.message.answer('❌ Курс не найден. Начните курс заново.')
        return
    
    # Получаем прогресс пользователя по конкретной воронке
    user_progress = await get_user_funnel_progress(session, callback.from_user.id, current_funnel_id)
    
    if not user_progress:
        await callback.message.answer('❌ Прогресс не найден. Начните курс заново.')
        return
    
    # Показываем прогресс
    funnel_with_steps = await get_funnel_with_steps(session, current_funnel_id)
    total_steps = len(funnel_with_steps.steps) if funnel_with_steps else 0
    
    progress_text = f'📊 <b>Ваш прогресс в курсе "{current_funnel.name}"</b>\n\n'
    progress_text += f'📈 <b>Этап:</b> {user_progress.current_step} из {total_steps}\n'
    progress_text += f'📅 <b>Начато:</b> {user_progress.started_at.strftime("%d.%m.%Y")}\n'
    
    if user_progress.is_completed and user_progress.current_step == total_steps:
        progress_text += f'✅ <b>Статус:</b> Завершено\n'
        progress_text += f'🎯 <b>Завершено:</b> {user_progress.completed_at.strftime("%d.%m.%Y")}\n'
    else:
        progress_text += f'🔄 <b>Статус:</b> В процессе\n'
        # Сбрасываем флаг только если он был установлен неправильно
        if user_progress.is_completed:
            user_progress.is_completed = False
            user_progress.completed_at = None
            await session.commit()
        
        # Показываем информацию о следующем этапе
        if user_progress.current_step <= total_steps and funnel_with_steps:
            current_step = funnel_with_steps.steps[user_progress.current_step - 1]
            progress_text += f'📚 <b>Следующий урок:</b> {current_step.title}\n'
            progress_text += f'💰 <b>Тип:</b> {"Бесплатный" if current_step.is_free else "Платный"}\n'
    
    await callback.message.answer(progress_text, reply_markup=user_kb.back_mrk)

# Обработчики для платных этапов (когда пользователь останавливается)
@funnel_user_router.callback_query(F.data=='consultation_request')
async def consultation_request_handler(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.answer(
        '💼 <b>Запись на консультацию</b>\n\n'
        'Для продолжения обучения и получения индивидуальной поддержки:\n\n'
        '📞 <b>Свяжитесь с психологом:</b> @Olesja_Chernova\n\n'
        '💬 Напишите психологу для записи на консультацию\n\n'
        '🎯 <b>Что вы получите:</b>\n'
        '• Индивидуальный подход\n'
        '• Продолжение обучения\n'
        '• Персональные рекомендации\n'
        '• Поддержку в процессе',
        reply_markup=funnel_kb.funnel_continue_kb
    )

@funnel_user_router.callback_query(F.data=='more_materials')
async def more_materials_handler(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.answer(
        '📚 <b>Дополнительные материалы</b>\n\n'
        'Полезные ресурсы для вашего развития:\n\n'
        '📖 <b>Записи эфиров:</b> https://t.me/+vQ_g1edapwM2YmQy\n'
        '⭐ <b>Отзывы клиентов:</b> https://t.me/+znP0wsKNCENlMmVi\n'
        '🎁 <b>Бесплатные материалы:</b> https://t.me/+OISLRdIfqhBiYzBi\n\n'
        '💼 <b>Записаться на консультацию:</b> @Olesja_Chernova',
        reply_markup=user_kb.back_mrk
    )

@funnel_user_router.callback_query(F.data=='restart_course')
async def restart_course_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer('')
    
    # Получаем ID текущей воронки из state
    data = await state.get_data()
    current_funnel_id = data.get('current_funnel_id')
    
    if current_funnel_id:
        # Перезапускаем текущий курс
        current_funnel = await session.get(Funnel, current_funnel_id)
        if current_funnel and current_funnel.is_active:
            # Сбрасываем прогресс пользователя
            await reset_user_funnel_progress(session, callback.from_user.id, current_funnel_id)
            # Начинаем курс заново
            await start_course_for_user(callback.message, session, current_funnel, state)
            return
    
    # Если не нашли текущий курс, начинаем первый доступный
    funnels = await get_active_funnels(session)
    if funnels:
        await start_course_for_user(callback.message, session, funnels[0], state)
    else:
        await callback.message.answer('❌ Курс недоступен.')

@funnel_user_router.callback_query(F.data=='my_courses')
async def show_my_courses(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer('')
    
    # Получаем все прогрессы пользователя
    user_progresses = await get_user_all_funnel_progress(session, callback.from_user.id)
    
    if not user_progresses:
        await callback.message.answer(
            '📚 <b>Ваши курсы</b>\n\n'
            'У вас пока нет активных курсов.\n\n'
            '🎁 Начните бесплатный курс прямо сейчас!',
            reply_markup=user_kb.start_kb.as_markup()
        )
        return
    
    text = '📚 <b>Ваши курсы</b>\n\n'
    
    for progress in user_progresses:
        funnel = await session.get(Funnel, progress.funnel_id)
        if funnel and funnel.is_active:
            funnel_with_steps = await get_funnel_with_steps(session, funnel.id)
            total_steps = len(funnel_with_steps.steps) if funnel_with_steps else 0
            
            text += f'📋 <b>{funnel.name}</b>\n'
            text += f'📈 Прогресс: {progress.current_step} из {total_steps}\n'
            
            if progress.is_completed and progress.current_step == total_steps:
                text += f'✅ Статус: Завершен\n'
                text += f'🎯 Завершен: {progress.completed_at.strftime("%d.%m.%Y")}\n'
            else:
                text += f'🔄 Статус: В процессе\n'
                text += f'📅 Начат: {progress.started_at.strftime("%d.%m.%Y")}\n'
                # Сбрасываем флаг только если он был установлен неправильно
                if progress.is_completed:
                    progress.is_completed = False
                    progress.completed_at = None
                    await session.commit()
            
            text += '\n'
    
    # Добавляем кнопки для управления
    kb = InlineKeyboardBuilder()
    kb.button(text='🎁 Начать новый курс', callback_data='start_funnel')
    kb.button(text='🔙 В главное меню', callback_data='back')
    kb.adjust(1)
    
    await callback.message.answer(text, reply_markup=kb.as_markup())
