import os
from dotenv import load_dotenv

load_dotenv()

# Основные настройки
BOT_TOKEN = os.getenv('TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

DB_URL = os.getenv('DB_URL')
if not DB_URL:
    raise ValueError("DB_URL environment variable is not set")

# ID администратора (замените на реальный ID)
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

# ID канала для подписки
CHANNEL_ID = -1002726677960

# Ограничения
MAX_BOOKINGS_PER_USER = 3

# URL-адреса
CHANNEL_URL = 'https://t.me/+k0hD8nKBAg43Yzky'
RECORDINGS_URL = 'https://t.me/+vQ_g1edapwM2YmQy'
REVIEWS_URL = 'https://t.me/+znP0wsKNCENlMmVi'
GIFT_URL = 'https://t.me/+OISLRdIfqhBiYzBi' 