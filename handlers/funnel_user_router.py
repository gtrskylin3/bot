from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

import keyboards.funnel_kb as funnel_kb
import keyboards.user_kb as user_kb
from database.orm_query import get_active_funnels, start_user_funnel, get_user_funnel_progress, get_funnel_with_steps, advance_user_funnel
from database.models import FunnelProgress, Funnel

# Создаем роутер для пользователей в воронке
funnel_user_router = Router()

# Функция для отправки этапа воронки
async def send_funnel_step(message: Message, session: AsyncSession, progress: FunnelProgress, funnel: Funnel):
    """Отправляет этап воронки пользователю"""
    funnel_with_steps = await get_funnel_with_steps(session, funnel.id)
    
    if progress.current_step > len(funnel_with_steps.steps):
        await message.answer('❌ Этап не найден')
        return
    
    current_step = funnel_with_steps.steps[progress.current_step - 1]
    
    # Формируем текст сообщения
    step_text = f'📚 <b>{current_step.title}</b>\n\n'
    
    # Выбираем клавиатуру в зависимости от типа этапа
    if not current_step.is_free:
        reply_markup = funnel_kb.funnel_paid_kb
    else:
        reply_markup = funnel_kb.funnel_next_kb
    
    # Отправляем контент в зависимости от типа
    if current_step.content_type == 'video' and current_step.file_id:
        # Отправляем видео с подписью
        caption = f'{step_text}{current_step.content}\n\n'
        if not current_step.is_free:
            caption += '💰 <b>Это платный этап</b>\n'
            caption += 'Для продолжения запишитесь на консультацию к психологу.\n'
        
        await message.answer_video(
            video=current_step.file_id,
            caption=caption,
            reply_markup=reply_markup
        )
    else:
        # Отправляем только текст
        step_text += f'{current_step.content}\n\n'
        if not current_step.is_free:
            step_text += '💰 <b>Это платный этап</b>\n'
            step_text += 'Для продолжения запишитесь на консультацию к психологу.\n'
        
        await message.answer(step_text, reply_markup=reply_markup) 




# Начало воронки для пользователя
@funnel_user_router.callback_query(F.data=='start_funnel')
async def start_funnel_for_user(callback: CallbackQuery, session: AsyncSession):
    await callback.answer('')

    funnels = await get_active_funnels(session)

    if not funnels:
        await callback.message.answer(
            '❌ В данный момент нет доступных курсов.\nПопробуйте позже!',
            reply_markup=user_kb.back_mrk
        )
        return
    
    funnel = funnels[0]
    progress = await start_user_funnel(session, callback.from_user.id, funnel.id)

    await send_funnel_step(callback.message, session, progress, funnel)
    
# Переход к следующему этапу воронки
@funnel_user_router.callback_query(F.data=='funnel_next')
async def next_funnel_step(callback: CallbackQuery, session: AsyncSession):
    await callback.answer('')
    
    # Получаем прогресс пользователя
    funnels = await get_active_funnels(session)
    if not funnels:
        await callback.message.answer('❌ Воронка недоступна')
        return
    funnel = funnels[0]
    progress = await get_user_funnel_progress(session, callback.from_user.id, funnel.id)
    
    if not progress:
        await callback.message.answer('❌ Прогресс не найден')
        return
    
    if progress.is_completed:
        await callback.message.answer(
            '🎉 <b>Поздравляем! Вы завершили курс!</b>\n\n'
            'Теперь вы можете записаться на индивидуальную консультацию.',
            reply_markup=funnel_kb.funnel_complete_kb
        )
    else:
        # Переходим к следующему этапу
        progress = await advance_user_funnel(session, callback.from_user.id, funnel.id)
        await send_funnel_step(callback.message, session, progress, funnel)

# Показ прогресса пользователя
@funnel_user_router.callback_query(F.data=='funnel_progress')
async def show_funnel_progress(callback: CallbackQuery, session: AsyncSession):
    await callback.answer('')
    
    funnels = await get_active_funnels(session)
    if not funnels:
        await callback.message.answer('❌ Воронка недоступна')
        return
    
    funnel = funnels[0]
    progress = await get_user_funnel_progress(session, callback.from_user.id, funnel.id)
    
    if not progress:
        await callback.message.answer('❌ Прогресс не найден')
        return
    
    # Показываем прогресс
    funnel_with_steps = await get_funnel_with_steps(session, funnel.id)
    total_steps = len(funnel_with_steps.steps)
    
    progress_text = f'📊 <b>Ваш прогресс в курсе "{funnel.name}"</b>\n\n'
    progress_text += f'📈 <b>Этап:</b> {progress.current_step} из {total_steps}\n'
    progress_text += f'📅 <b>Начато:</b> {progress.started_at.strftime("%d.%m.%Y")}\n'
    
    if progress.is_completed:
        progress_text += f'✅ <b>Статус:</b> Завершено\n'
        progress_text += f'🎯 <b>Завершено:</b> {progress.completed_at.strftime("%d.%m.%Y")}\n'
    else:
        progress_text += f'🔄 <b>Статус:</b> В процессе\n'
    
    await callback.message.answer(progress_text, reply_markup=user_kb.back_mrk)
