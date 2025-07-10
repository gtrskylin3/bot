from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton



start_kb = InlineKeyboardBuilder()
# start_kb.button(text='Мои услуги', callback_data='service_list')
start_kb.button(text='💼 Записаться', callback_data='service_list')
start_kb.button(text='🎁 Получить курс', callback_data='start_funnel')
start_kb.button(text='👤 Ваш профиль', callback_data='user_profile')
start_kb.button(text='📺 Записи эфиров', url='https://t.me/+vQ_g1edapwM2YmQy')
start_kb.button(text='💬 Отзывы', url='https://t.me/+znP0wsKNCENlMmVi')
start_kb.adjust(2)

back_btn = InlineKeyboardButton(text='🔙 Вернуться в меню', callback_data='back')

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

contact_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Поделиться контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

start_course_kb = InlineKeyboardBuilder()
start_course_kb.button(text='🎁 Начать курс', callback_data='start_funnel')
start_course_kb.button(text='🔙 Вернуться в меню', callback_data='back')
start_course_kb.adjust(1)


phone_kb = InlineKeyboardBuilder()
phone_kb.button(text = "📞 Изменить номер", callback_data="change_user_phone")
phone_kb.adjust(1)

user_profile_kb = InlineKeyboardBuilder()
user_profile_kb.button(text='📞 Изменить номер', callback_data='change_user_phone')
user_profile_kb.button(text='📚 Мои курсы', callback_data='my_courses')
user_profile_kb.button(text='🔙 Вернуться в меню', callback_data='back')
user_profile_kb.adjust(1)