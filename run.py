import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
import logging
from handlers.user_router import user_router
from handlers.admin_router import admin_router


load_dotenv()

bot = Bot(token=os.getenv('TOKEN')) 
dp = Dispatcher()
dp.include_routers(admin_router, user_router)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO) 
    asyncio.run(main())