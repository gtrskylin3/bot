import os
from dotenv import load_dotenv
from aiogram.filters import BaseFilter
from aiogram.types import Message

load_dotenv(override=True)

admin = os.getenv('ADMIN')

class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool | dict:
        admins: list[int] = [int(admin)]
        if message.from_user.id in admins:
            return True
        return False