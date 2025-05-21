from aiogram.utils.keyboard import InlineKeyboardBuilder

start_kb = InlineKeyboardBuilder()
start_kb.button(text='Мои услуги', callback_data='service_list')
start_kb.button(text='Записаться', callback_data='redirect_ls')
start_kb.button(text='Отзывы', callback_data='reviews')
start_kb.adjust(1)