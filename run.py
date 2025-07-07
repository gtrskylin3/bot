import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from handlers.user_router import user_router
from handlers.admin_router import admin_router
from handlers.funnel_admin_router import funnel_admin_router
from handlers.funnel_user_router import funnel_user_router
from middleware.db import DataBaseSession
from database.engine import create_db, session_maker
from handlers.broadcast_router import broadcast_router
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)) 
dp = Dispatcher()
dp.include_routers(admin_router, funnel_admin_router, funnel_user_router, broadcast_router, user_router)

async def main():
    dp.update.middleware(DataBaseSession(session_pool=session_maker))
    await create_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO) 
    asyncio.run(main()) 