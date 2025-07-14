import asyncio
import logging
from typing import Callable
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import get_active_users, deactivate_user

async def send_broadcast(
    bot: Bot,
    session: AsyncSession,
    send_func: Callable,
    content_type: str,
    **kwargs
    )-> tuple[int, int]:
    """
    Общая функция для рассылки с обработкой лимитов Telegram
    
    Args:
        bot: Экземпляр бота
        session: Сессия БД
        send_func: Функция отправки (bot.send_message, bot.send_video и т.д.)
        content_type: Тип контента для логирования
        **kwargs: Аргументы для функции отправки
    
    Returns:
        tuple[int, int]: (success_count, failed_count)
    """
    users = await get_active_users(session)
    if not users:
        return 0, 0
    
    success_count = 0
    failed_count = 0
    batch_size = 30  # Лимит Telegram: 30 сообщений в секунду
    delay = 1.0
    
    for i in range(0, len(users), batch_size):
        batch = users[i:i+batch_size]
        tasks = []
        for user in batch:
            task = send_func(chat_id=str(user.tg_id), **kwargs)
            tasks.append((user, task))
        for user, task in tasks:
            try:
                await task
                success_count += 1
            except Exception as e:
                failed_count += 1
                await deactivate_user(session, user.tg_id)
                logging.exception(f"Ошибка отправки пользователю:  {user.tg_id}")
        if i + batch_size < len(users):
            await asyncio.sleep(delay)
    return success_count, failed_count

def format_broadcast_result(
    success_count: int, 
    failed_count: int, 
    content_type: str, 
    content_description: str
    ) -> str:
    """
    Форматирует результат рассылки в читаемый вид
    
    Args:
        success_count: Количество успешных отправок
        failed_count: Количество неудачных отправок
        content_type: Тип контента (текст, видео и т.д.)
        content_description: Описание контента
    
    Returns:
        str: Отформатированное сообщение о результате
    """
    if success_count > 0 or failed_count > 0:
        return (
            f"✅ Рассылка {content_type} завершена!\n\n"
            f"📤 Отправлено: {success_count}\n"
            f"❌ Ошибок: {failed_count}\n\n"
            f"📝 Контент: <i>\"{content_description}\"</i>"
        )
    else:
        return "Список пользователей пуст"