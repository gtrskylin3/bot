from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from keyboards.user_menu import set_user_menu
from aiogram.filters import CommandStart, Command
import keyboards.user_kb as user_kb

users = {}
user_router = Router()
user_router.startup.register(set_user_menu)
image = FSInputFile("start.webp", filename='olesya.webp')


@user_router.message(CommandStart())
async def start(message: Message):
    if message.chat.id not in users:
        users[message.from_user.full_name] = message.chat.id
    await message.answer_photo(photo=image, caption='Привет я Чернова Олеся <b>Психолог</b>\n' \
    'Работаю со взрослыми и детьми!❤\nИндивидуально и в группах.\n<b>Конфиденциально!</b>\n<b>Безопасно!</b>\n<b>Онлайн и оффлайн.</b>', reply_markup=user_kb.start_kb.as_markup())
    print(users)

@user_router.message(Command(commands='help'))
async def help_cmd(message: Message):
    await message.answer('Это бот где <b>вы можете</b>:\n\nПолучать уведомления об эфирах\n'
    'Изучить доступные услуги и цены\n\n<b>Все просто и удобно❤</b>', reply_markup=user_kb.start_kb.as_markup())

@user_router.callback_query(F.data=='service_list')
async def service_list(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("""Мои услуги
-<b>Первая</b>
-<b>Вторая</b>
-<b>Третья</b>""", reply_markup=user_kb.back_mrk)
    await callback.answer('Мои услуги')

@user_router.callback_query(F.data=='back')
async def back(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer_photo(photo=image, caption='Привет я Чернова Олеся <b>Психолог</b>\n' \
    'Работаю со взрослыми и детьми!❤\nИндивидуально и в группах.\n<b>Конфиденциально!</b>\n<b>Безопасно!</b>\n<b>Онлайн и оффлайн.</b>', reply_markup=user_kb.start_kb.as_markup())

@user_router.message()
async def spam(message: Message):
    await message.answer('Воспользуйтесь меню для навигации')

