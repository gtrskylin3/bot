from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup



start_kb = InlineKeyboardBuilder()
# start_kb.button(text='Мои услуги', callback_data='service_list')
start_kb.button(text='💼 Записаться', callback_data='service_list')
start_kb.button(text='🎁 Получить курс', callback_data='start_funnel')
start_kb.button(text='📚 Мои курсы', callback_data='my_courses')
start_kb.button(text='📺 Записи эфиров', url='https://t.me/+vQ_g1edapwM2YmQy')
start_kb.button(text='💬 Отзывы', url='https://t.me/+znP0wsKNCENlMmVi')
start_kb.adjust(2)

back_btn = InlineKeyboardButton(text='Вернуться в меню', callback_data='back')

back_mrk = InlineKeyboardMarkup(inline_keyboard=[
    [back_btn]
])

gift_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Забрать подарок', url='https://t.me/+OISLRdIfqhBiYzBi')],
    [back_btn]
])

sub_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Подписаться', url='https://t.me/+k0hD8nKBAg43Yzky')],
    [InlineKeyboardButton(text='Получить подарок🎁', callback_data='check_sub')]
])