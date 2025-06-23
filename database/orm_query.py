from sqlalchemy import select, insert, update, delete
from database.models import User, BroadcastSettings
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

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



