from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

start_kb = InlineKeyboardBuilder()
start_kb.button(text='Мои услуги', callback_data='service_list')
start_kb.button(text='Записи эфиров', url='https://t.me/+vQ_g1edapwM2YmQy')
start_kb.button(text='Записаться', url='https://t.me/Olesja_Chernova')
start_kb.button(text='Отзывы', url='https://t.me/+znP0wsKNCENlMmVi')
start_kb.adjust(2)

back_btn = InlineKeyboardButton(text='Вернуться', callback_data='back')
back_mrk = InlineKeyboardMarkup(inline_keyboard=[
    [back_btn]
])
