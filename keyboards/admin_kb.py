from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

admin_kb = InlineKeyboardBuilder()
admin_kb.button(text='📝 Рассылка текста', callback_data='send_all')
admin_kb.button(text='📹 Рассылка видео', callback_data='send_video')
admin_kb.button(text='👥 Посмотреть список пользователей', callback_data='user_list')
admin_kb.button(text='➕ Добавить услугу', callback_data='add_service')
admin_kb.button(text='👀 Посмотреть услуги', callback_data='view_services')
admin_kb.adjust(1)

broadcast_kb = InlineKeyboardBuilder()
broadcast_kb.button(text=f'📤 Стандартный текст', callback_data='send_default')
broadcast_kb.button(text='✏️ Кастомный текст', callback_data='send_custom')
broadcast_kb.button(text='⚙️ Изменить стандартный текст', callback_data='change_default')
broadcast_kb.button(text='🔙 Назад', callback_data='back_to_admin')
broadcast_kb.adjust(2)

back_to_admin = InlineKeyboardBuilder()
back_to_admin.button(text='Вернуться в меню', callback_data='back_to_admin')
back_to_admin.adjust(1)

delete_confirm = InlineKeyboardBuilder() 
delete_confirm.button(text='Да', callback_data='confirm_delete')
delete_confirm.button(text='Нет', callback_data='back_to_admin')
delete_confirm.adjust(1)


