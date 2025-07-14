import logging
import os
from logging.handlers import RotatingFileHandler
from config import BASE_DIR


log_file = os.path.join(BASE_DIR, 'bot.log')

def configure_logging(level=logging.WARNING):
    handlers = [
        logging.StreamHandler(),
        RotatingFileHandler(
            filename=log_file,
            maxBytes=10*1024*1024,  # Максимальный размер файла в байтах (например, 10 МБ)
            backupCount=0,  # Не сохраняем резервные копии
            encoding='utf-8'
        )
    ]
    logging.basicConfig(
        level=level,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)7s - %(message)s",
        handlers=handlers
    )
    # Устанавливаем уровень логирования для aiogram и других шумных библиотек
    noisy_loggers = [
        'aiogram', 
        'sqlalchemy', 
        'asyncio',
        'aiohttp',
        'aiosqlite'
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    