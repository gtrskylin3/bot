import os
from dotenv import load_dotenv
from aiogram.filters import BaseFilter
from aiogram.types import Message

load_dotenv()



class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool | dict:
        admins: list[int] = [int(os.getenv('ADMIN'))]
        if message.from_user.id in admins:
            return True
        return False