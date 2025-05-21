from aiogram.utils.keyboard import InlineKeyboardBuilder

admin_kb = InlineKeyboardBuilder()
admin_kb.button(text='Рассылку', callback_data='send_all')
admin_kb.button(text='Посмотреть список пользователей', callback_data='user_list')
admin_kb.adjust(1)