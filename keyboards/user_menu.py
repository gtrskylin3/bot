from aiogram import Bot
from aiogram.types import BotCommand


async def set_user_menu(bot: Bot):

    main_menu_commands = [
        BotCommand(command='/start',
        description='Главная'),
        BotCommand(command='/help', 
        description='Возможности бота')
    ]

    await bot.set_my_commands(main_menu_commands)