from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

admin_kb = InlineKeyboardBuilder()
admin_kb.button(text='📤 Рассылка', callback_data='broadcast_menu')
admin_kb.button(text='📋 Просмотр записей', callback_data='view_bookings')
admin_kb.button(text='➕ Добавить услугу', callback_data='add_service')
admin_kb.button(text='👀 Посмотреть услуги', callback_data='view_services')
admin_kb.button(text='👥 Управление воронками', callback_data='manage_funnels')
admin_kb.button(text='👥 Посмотреть список пользователей', callback_data='user_list')
admin_kb.adjust(2)

broadcast_menu = InlineKeyboardBuilder()
broadcast_menu.button(text='📝 Рассылка текста', callback_data='send_all')
broadcast_menu.button(text='📹 Рассылка видео', callback_data='send_video')
broadcast_menu.button(text='🟡 Рассылка кружка', callback_data='send_video_note')
broadcast_menu.button(text='🔙 Назад', callback_data='back_to_admin')
broadcast_menu.adjust(1)



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
delete_confirm.button(text='Да', callback_data='confirm_delete_service')
delete_confirm.button(text='Нет', callback_data='back_to_admin')
delete_confirm.adjust(1)

confirm_send_video = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text='✅ Подтвердить', callback_data='confirm_send_video')],
                [InlineKeyboardButton(text='✏️ Изменить подпись', callback_data='edit_caption')],
                [InlineKeyboardButton(text='❌ Отмена', callback_data='broadcast_menu')]
            ]
)
confirm_send_video_note = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text='✅ Подтвердить', callback_data='confirm_send_video_note')],
                [InlineKeyboardButton(text='❌ Отмена', callback_data='broadcast_menu')]
            ]
)

# Клавиатура подтверждения рассылки текста
confirm_send_custom_text = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='✅ Подтвердить', callback_data='confirm_send_text')],
        [InlineKeyboardButton(text='✏️ Изменить текст', callback_data='edit_custom_text')],
        [InlineKeyboardButton(text='❌ Отмена', callback_data='broadcast_menu')]
    ]
)

confirm_send_default_text = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='✅ Подтвердить', callback_data='confirm_send_text')],
        [InlineKeyboardButton(text='✏️ Изменить текст', callback_data='change_default')],
        [InlineKeyboardButton(text='❌ Отмена', callback_data='broadcast_menu')]
    ]
)

def get_booking_actions_kb(booking_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления записью"""
    buttons = []
    
    buttons.extend([
            [InlineKeyboardButton(text='🎉 Завершить и удалить', callback_data=f'booking_complete_{booking_id}')],
            [InlineKeyboardButton(text='❌ Отменить и удалить', callback_data=f'booking_cancel_{booking_id}')]
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

review_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Отзывы', url='https://t.me/+znP0wsKNCENlMmVi')]
    ]
)