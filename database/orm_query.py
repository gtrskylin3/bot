from sqlalchemy import select, insert, update, delete
from database.models import User, BroadcastSettings, Booking, Funnel, FunnelStep, FunnelProgress
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta


async def get_or_create_user(session: AsyncSession, user_tg_id: int, user_name: str) -> User:
    """Получает пользователя из БД или создает нового. Возвращает объект пользователя."""
    current_user = await session.get(User, user_tg_id)
    if current_user is None:
        # Создаем нового пользователя
        current_user = User(tg_id=user_tg_id, name=user_name)
        session.add(current_user)
        await session.commit()
        return current_user
    else:
        # Обновляем имя если изменилось и активируем пользователя
        if current_user.name != user_name:
            current_user.name = user_name
        if not current_user.is_active:
            current_user.is_active = True
        await session.commit()
        return current_user

async def deactivate_user(session: AsyncSession, user_tg_id: int):
    """Деактивирует пользователя (при блокировке бота)"""
    current_user = await session.get(User, user_tg_id)
    if current_user and current_user.is_active:
        current_user.is_active = False
        await session.commit()

async def get_active_users(session: AsyncSession):
    """Получает всех активных пользователей для рассылки"""
    users = await session.scalars(select(User).where(User.is_active == True))
    return list(users)

async def get_or_create_broadcast_settings(session: AsyncSession) -> BroadcastSettings:
    """Получает настройки рассылки админа или создает новые"""
    settings = await session.scalars(select(BroadcastSettings))
    settings = settings.first()
    if settings is None:
        settings = BroadcastSettings()
        session.add(settings)
        await session.commit()
    return settings

async def update_default_broadcast_text(session: AsyncSession, new_text: str):
    """Обновляет стандартный текст рассылки для админа"""
    settings = await get_or_create_broadcast_settings(session)
    settings.default_text = new_text
    await session.commit()
    return settings


async def create_booking(
    session: AsyncSession,
    user_tg_id: int,
    service_id: int,
    client_name: str,
    phone: str,
    preferred_date: str,
    preferred_time: str,
) -> Booking:
    """Создает новую запись"""
    booking = Booking(
        user_tg_id=user_tg_id,
        service_id=service_id,
        client_name=client_name,
        phone=phone,
        preferred_date=preferred_date,
        preferred_time=preferred_time
    )
    session.add(booking)
    await session.commit()
    return booking

async def get_all_bookings(session: AsyncSession):
    """Получает все записи (for admin)"""
    query = select(Booking).options(selectinload(Booking.service)).order_by(Booking.created_at.desc())
    bookings = await session.scalars(query)
    return list(bookings)

async def get_user_bookings(session: AsyncSession, user_id: int):
    """Получает записи пользователя по его id"""
    user_bookings = await session.scalars(select(Booking).where(Booking.user_tg_id == user_id))
    return len(list(user_bookings))


async def delete_booking(session: AsyncSession, booking_id: int):
    """Удаляет запись (for admin)"""
    booking = await session.get(Booking, booking_id)
    if booking:
        await session.execute(delete(Booking).where(Booking.id == booking_id))
        await session.commit()
        return booking.user_tg_id
    return None


# Функции для работы с воронками

async def create_funnel(session: AsyncSession, name: str, description: str = None) -> Funnel:
    """Создает новую воронку"""
    funnel = Funnel(name=name, description=description)
    session.add(funnel)
    await session.commit()
    return funnel

async def get_active_funnels(session: AsyncSession) -> list[Funnel]:
    """Получает все активные воронки"""
    funnels = await session.scalars(select(Funnel).where(Funnel.is_active == True))
    return list(funnels)

async def get_all_funnels(session: AsyncSession) -> list[Funnel]:
    """Получает все воронки"""
    funnels = await session.scalars(select(Funnel))
    return list(funnels)

async def get_funnel_with_steps(session: AsyncSession, funnel_id: int) -> Funnel:
    """Получает воронку с этапами"""
    funnel = await session.scalar(
        select(Funnel)
        .options(selectinload(Funnel.steps))
        .where(Funnel.id == funnel_id)
    )
    return funnel

async def deactivate_or_activate_funnel(session: AsyncSession, funnel_id: int, is_active: bool):
    """Деактивирует воронку"""
    funnel = await session.get(Funnel, funnel_id)
    if funnel:
        funnel.is_active = is_active
        await session.commit()
        return funnel
    return None


async def create_funnel_step(
    session: AsyncSession,
    funnel_id: int,
    order: int,
    title: str,
    content: str,
    content_type: str,
    is_free: bool = True,
    file_id: str = None
) -> FunnelStep:
    """Создает новый этап воронки"""
    step = FunnelStep(
        funnel_id=funnel_id,
        order=order,
        title=title,
        content=content,
        content_type=content_type,
        is_free=is_free,
        file_id=file_id
    )
    session.add(step)
    await session.commit()
    return step

async def get_user_funnel_progress(session: AsyncSession, user_tg_id: int, funnel_id: int) -> FunnelProgress:
    """Получает прогресс пользователя по воронке"""
    progress = await session.scalar(
        select(FunnelProgress)
        .where(FunnelProgress.user_tg_id == user_tg_id)
        .where(FunnelProgress.funnel_id == funnel_id)
    )
    return progress

async def start_user_funnel(session: AsyncSession, user_tg_id: int, funnel_id: int) -> FunnelProgress:
    """Начинает воронку для пользователя"""
    # Проверяем, не начал ли уже пользователь эту воронку
    existing_progress = await get_user_funnel_progress(session, user_tg_id, funnel_id)
    if existing_progress:
        return existing_progress
    
    # Создаем новый прогресс
    progress = FunnelProgress(
        user_tg_id=user_tg_id,
        funnel_id=funnel_id,
        current_step=1,
    )
    session.add(progress)
    await session.commit()
    return progress

async def advance_user_funnel(session: AsyncSession, user_tg_id: int, funnel_id: int) -> FunnelProgress:
    """Переходит к следующему этапу воронки"""
    progress = await get_user_funnel_progress(session, user_tg_id, funnel_id)
    if not progress:
        return None
    
    # Получаем воронку с этапами
    funnel = await get_funnel_with_steps(session, funnel_id)
    if not funnel or not funnel.steps:
        return progress
    
    total_steps = len(funnel.steps)
    
    # Проверяем, что текущий этап существует
    if progress.current_step > total_steps:
        return progress
    
    # Получаем текущий этап
    current_step = funnel.steps[progress.current_step - 1]
    
    # Если текущий этап платный, не переходим дальше
    if not current_step.is_free:
        return progress
    
    # Переходим к следующему этапу
    progress.current_step += 1
    progress.last_activity = datetime.now()
    
    # Проверяем, достигли ли мы конца курса
    if progress.current_step > total_steps:
        # Курс завершен - мы прошли все этапы
        progress.is_completed = True
        progress.completed_at = datetime.now()
    else:
        # Проверяем, не стал ли следующий этап платным
        next_step = funnel.steps[progress.current_step - 1]
        if not next_step.is_free:
            # Следующий этап платный - курс завершен на бесплатной части
            progress.is_completed = True
            progress.completed_at = datetime.now()
    
    await session.commit()
    return progress

async def reset_user_funnel_progress(session: AsyncSession, user_tg_id: int, funnel_id: int) -> FunnelProgress:
    """Сбрасывает прогресс пользователя по воронке к началу"""
    progress = await get_user_funnel_progress(session, user_tg_id, funnel_id)
    if progress:
        progress.current_step = 1
        progress.is_completed = False
        progress.completed_at = None
        progress.last_activity = datetime.now()
        await session.commit()
    return progress

async def delete_funnel(session: AsyncSession, funnel_id: int):
    """Удаляет воронку и все связанные с ней данные"""
    # Удаляем прогресс пользователей
    await session.execute(delete(FunnelProgress).where(FunnelProgress.funnel_id == funnel_id))
    # Удаляем этапы
    await session.execute(delete(FunnelStep).where(FunnelStep.funnel_id == funnel_id))
    # Удаляем воронку
    await session.execute(delete(Funnel).where(Funnel.id == funnel_id))
    await session.commit()

async def get_user_all_funnel_progress(session: AsyncSession, user_tg_id: int) -> list[FunnelProgress]:
    """Получает все прогрессы пользователя по воронкам"""
    progress_list = await session.scalars(
        select(FunnelProgress)
        .where(FunnelProgress.user_tg_id == user_tg_id)
        .order_by(FunnelProgress.started_at.desc())
    )
    return list(progress_list)
