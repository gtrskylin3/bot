import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, User, user
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import exc
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State 
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
    get_user_all_funnel_progress,
    check_user_phone,
    update_phone
)
from database.models import FunnelProgress, Funnel
import phonenumbers
from filters.admin_filter import admin 

# Создаем роутер для пользователей в воронке
funnel_user_router = Router()

class Register(StatesGroup):
    waiting_for_phone = State()


# Функция для отправки уведомления админу
async def send_admin_notification(bot, user_id: int, username: str, notification_type: str, session: AsyncSession, **kwargs):
    """Отправляет уведомление админу о действиях пользователя в курсе"""
    try:
        if notification_type == "course_started":
            admin_text = f"🎯 <b>Пользователь начал курс!</b>\n\n"
            admin_text += f"👤 <b>Пользователь:</b> @{username or 'Без username'}\n"
            admin_text += f"🆔 <b>Telegram ID:</b> {user_id}\n"
            admin_text += f"📚 <b>Курс:</b> {kwargs.get('course_name', 'Неизвестный')}\n"
            admin_text += f"📅 <b>Дата начала:</b> {kwargs.get("started_at", datetime.now()).strftime('%d.%m.%Y %H:%M')}\n"
            
        elif notification_type == "course_completed":
            admin_text = f"🎉 <b>Пользователь завершил курс!</b>\n\n"
            admin_text += f"👤 <b>Пользователь:</b> @{username or 'Без username'}\n"
            admin_text += f"🆔 <b>Telegram ID:</b> {user_id}\n"
            admin_text += f"📞 <b>Телефон:</b> {await check_user_phone(session, user_id)}\n"
            admin_text += f"📚 <b>Курс:</b> {kwargs.get('course_name', 'Неизвестный')}\n"
            admin_text += f"📊 <b>Пройдено этапов:</b> {kwargs.get('total_steps', 0)}\n"
            admin_text += f"🎯 <b>Дата завершения:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            
        elif notification_type == "paid_step_reached":
            admin_text = f"💰 <b>Пользователь дошел до платного этапа!</b>\n\n"
            admin_text += f"👤 <b>Пользователь:</b> @{username or 'Без username'}\n"
            admin_text += f"🆔 <b>Telegram ID:</b> {user_id}\n"
            admin_text += f"📞 <b>Телефон:</b> {await check_user_phone(session, user_id)}\n"
            admin_text += f"📚 <b>Курс:</b> {kwargs.get('course_name', 'Неизвестный')}\n"
            admin_text += f"📊 <b>Пройдено этапов:</b> {kwargs.get('total_steps', 0)}\n"
            admin_text += f"🎯 <b>Дата завершения:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"

        elif notification_type == "consultation_requested":
            admin_text = f"📞 <b>Запрос на консультацию!</b>\n\n"
            admin_text += f"👤 <b>Пользователь:</b> @{username or 'Без username'}\n"
            admin_text += f"🆔 <b>Telegram ID:</b> {user_id}\n"
            admin_text += f"📞 <b>Телефон:</b> {await check_user_phone(session, user_id)}\n"
            admin_text += f"📚 <b>Курс:</b> {kwargs.get('course_name', 'Неизвестный')}\n"
            admin_text += f"📊 <b>Этап:</b> {kwargs.get('current_step', 0)} из {kwargs.get('total_steps', 0)}\n"
            admin_text += f"📅 <b>Дата запроса:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            
        elif notification_type == "registration_completed":
            admin_text = f"📝 <b>Новая регистрация!</b>\n\n"
            admin_text += f"👤 <b>Пользователь:</b> @{username or 'Без username'}\n"
            admin_text += f"🆔 <b>Telegram ID:</b> {user_id}\n"
            admin_text += f"📞 <b>Телефон:</b> {await check_user_phone(session, user_id)}\n"
            admin_text += f"📅 <b>Дата регистрации:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            
        else:
            return  # Неизвестный тип уведомления
            
        await bot.send_message(chat_id=admin, text=admin_text)
        
    except Exception as e:
        logging.exception("Ошибка отправки уведомления админу")

# Функция для отправки этапа воронки
async def send_funnel_step(message: Message, session: AsyncSession, progress: FunnelProgress, funnel: Funnel, user: User = None):
    """Отправляет этап воронки пользователю"""
    try:
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
        try:
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
        except Exception as e:
            logging.exception("Ошибка обновления прогресса")
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
                await send_admin_notification(bot=message.bot, user_id=user.id, username=user.username, notification_type="course_completed", session=session, course_name=funnel.name, total_steps=total_steps)
                logging.info("Пользователь: %d завершил курс (funnel id: %d)", user.id, funnel.id)
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
            await send_admin_notification(bot=message.bot, user_id=user.id, username=user.username, notification_type="paid_step_reached", session=session, course_name=funnel.name, total_steps=total_steps)
            logging.info("Пользователь: %d дошел до платного этапа курса (funnel id: %d)", user.id, funnel.id)
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
    except Exception as e:
        logging.exception("Ошибка при отправки этапа курса")

# Показ списка доступных курсов
@funnel_user_router.callback_query(F.data=='start_funnel')
async def show_available_courses(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    phone = await check_user_phone(session, callback.from_user.id)
    if phone is None:
        await callback.answer('')
        await state.set_state(Register.waiting_for_phone)
        await callback.message.answer("<b>Для прохождения курса:</b>\n\n"
                                      "📞 Введите ваш номер телефона:\n"
                                    "<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>\n\n"
                                    "<i>Отправте свой номер в чат</i>\n<i>Или поделитесь контктом нажав на кнопку</i>\n\n"
                                    "<i>Для отмены записи введите /cancel</i>",
                                      reply_markup=user_kb.contact_kb)
        return
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
        await start_course_for_user(callback.message, session, funnel, state, callback.from_user)
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

async def start_course_for_user(message: Message, session: AsyncSession, funnel: Funnel, state: FSMContext = None, user: User = None):
    """Начинает курс для пользователя"""
    # Получаем или создаем прогресс пользователя
    progress = await start_user_funnel(session, message.chat.id, funnel.id)
    await send_admin_notification(bot=message.bot, user_id=user.id, username=user.username, notification_type="course_started", session=session, course_name=funnel.name, started_at=progress.started_at)
    # Сохраняем ID воронки в state для правильной работы
    if state is not None:
        await state.update_data(current_funnel_id=funnel.id)
    
    # Отправляем первый этап
    await send_funnel_step(message, session, progress, funnel, user)

@funnel_user_router.message(Register.waiting_for_phone, Command('cancel'))
async def cancel_signup(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state and current_state.startswith("Register"):
        await state.clear()
        await message.answer(
            "Регистрация <b>отменена</b>",
            reply_markup=ReplyKeyboardRemove()
        )
        await message.answer("Без регестрации вам будут <b>не доступны</b> основные функции бота", reply_markup=user_kb.cancel_reg_kb.as_markup())
    else:
        await message.answer("Нет активной записи для отмены", reply_markup=ReplyKeyboardRemove())


@funnel_user_router.message(Register.waiting_for_phone)
async def get_phone(message: Message, state: FSMContext, session: AsyncSession):
    if message.contact:
        contact = message.contact
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
    else:
        phone = message.text.strip()
        if phone.startswith('8'):
            phone = '+7' + phone[1:]
        phone = phone.replace(' ', '')
        try:
            parsed_phone = phonenumbers.parse(phone, "RU")
            if not phonenumbers.is_valid_number(parsed_phone):
                await message.answer("❌ Неверный формат номера телефона. Попробуйте снова:\n\n<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>")
                return
            
            await state.update_data(phone=phone)
            await update_phone(session, message.from_user.id, phone)
        except phonenumbers.NumberParseException:
            await message.answer("❌ Неверный формат номера телефона. Попробуйте снова:\n\n<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>")
            return
    await state.clear()
    await message.answer(
    f"Вы успешно зарегестрированы\n<i>Ваш номер телефона:</i> <b>{phone}</b>",
    reply_markup=ReplyKeyboardRemove()
    )
    logging.info(f"Пользователь {message.from_user.id} успешно зарегестрирован.")
    await message.answer('Теперь вы можете проходить курсы', reply_markup=user_kb.start_course_kb.as_markup())
    
    


# Обработчик выбора конкретного курса
@funnel_user_router.callback_query(F.data.startswith('select_course:'))
async def select_course_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer('')
    
    try:
        # Извлекаем ID курса из callback_data
        funnel_id = int(callback.data.split(':')[1])
        funnel = await session.get(Funnel, funnel_id)
        
        if funnel and funnel.is_active:
            await start_course_for_user(callback.message, session, funnel, state, callback.from_user)
        else:
            await callback.message.answer('❌ Курс не найден или неактивен.')
    except (ValueError, IndexError):
        await callback.message.answer('❌ Ошибка при выборе курса.')
        logging.exception("❌ Ошибка при выборе курса.")

# Переход к следующему этапу воронки
@funnel_user_router.callback_query(F.data=='funnel_next')
async def next_funnel_step(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    try:
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
            await send_funnel_step(callback.message, session, updated_progress, current_funnel, callback.from_user)
            await callback.message.delete()
        else:
            await callback.message.answer('❌ Ошибка при переходе к следующему этапу.')
    except Exception:
        logging.exception("Ошибка при переходе к следующему этапу")

# Показ прогресса пользователя
@funnel_user_router.callback_query(F.data=='funnel_progress')
async def show_funnel_progress(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer('')
    
    # Получаем ID текущей воронки из state
    data = await state.get_data()
    current_funnel_id = data.get('current_funnel_id')
    
    if not current_funnel_id:
        await callback.message.answer('❌ Курс не найден. Начните курс заново.')
        logging.warning("Курс не найден. нету данных из state: current_funnel_id is None")
        return
    
    # Получаем текущую воронку
    current_funnel = await session.get(Funnel, current_funnel_id)
    if not current_funnel:
        logging.error(f"Нету воронки с id переданным из state: {current_funnel_id}")
        await callback.message.answer('❌ Курс не найден. Начните курс заново.')
        return
    
    # Получаем прогресс пользователя по конкретной воронке
    user_progress = await get_user_funnel_progress(session, callback.from_user.id, current_funnel_id)
    
    if not user_progress:
        logging.warning(f'❌ Прогресс user: {callback.from_user.id} не найден, current_funnel_id={current_funnel_id}')
        await callback.message.answer('❌ Прогресс не найден. Начните курс заново.')
        return
    
    # Показываем прогресс
    try:
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
    except Exception:
        logging.exception(F"Ошибка при получении воронки с этапами курса. User: {callback.from_user.id}, Funnel id: {current_funnel_id}")

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
            await start_course_for_user(callback.message, session, current_funnel, state, callback.from_user)
            return
    
    # Если не нашли текущий курс, начинаем первый доступный
    funnels = await get_active_funnels(session)
    if funnels:
        await start_course_for_user(callback.message, session, funnels[0], state, callback.from_user)
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
    
    try:
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
    except Exception:
        logging.exception(f"Ошибка при показе статистики курсов пользователя: {callback.from_user.id}")
    
    # Добавляем кнопки для управления
    kb = InlineKeyboardBuilder()
    kb.button(text='🎁 Начать новый курс', callback_data='start_funnel')
    kb.button(text='🔙 В главное меню', callback_data='back')
    kb.adjust(1)
    
    await callback.message.answer(text, reply_markup=kb.as_markup())
