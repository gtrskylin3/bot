from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


# Клавиатуры для админа (управление воронками)
admin_funnel_kb = InlineKeyboardBuilder()
admin_funnel_kb.button(text='➕ Создать воронку', callback_data='create_funnel')
admin_funnel_kb.button(text='📋 Список воронок', callback_data='list_funnels')
admin_funnel_kb.button(text='📊 Статистика', callback_data='funnel_stats')
admin_funnel_kb.button(text='🔙 Назад', callback_data='back_to_admin')
admin_funnel_kb.adjust(2)

# Клавиатура для управления конкретной воронкой
funnel_manage_kb = InlineKeyboardBuilder()
funnel_manage_kb.button(text='➕ Добавить этап', callback_data='add_funnel_step')
funnel_manage_kb.button(text='📋 Этапы воронки', callback_data='view_funnel_steps')
funnel_manage_kb.button(text='⚙️ Настройки', callback_data='funnel_settings')
funnel_manage_kb.button(text='❌ Удалить воронку', callback_data='delete_funnel')
funnel_manage_kb.button(text='🔙 Назад к воронкам', callback_data='list_funnels')
funnel_manage_kb.adjust(2)

# Клавиатура подтверждения удаления
delete_funnel_confirm = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅ Да, удалить', callback_data='confirm_delete_funnel')],
    [InlineKeyboardButton(text='❌ Отмена', callback_data='list_funnels')]
])

# Клавиатуры для пользователей (в воронке)
funnel_next_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='➡️ Следующий урок', callback_data='funnel_next')],
    [InlineKeyboardButton(text='📋 Мой прогресс', callback_data='funnel_progress')],
    [InlineKeyboardButton(text='🔙 В главное меню', callback_data='back')]
])

funnel_complete_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='💼 Записаться на консультацию', callback_data='service_list')],
    [InlineKeyboardButton(text='📚 Больше материалов', callback_data='more_content')],
    [InlineKeyboardButton(text='🔙 В главное меню', callback_data='back')]
])

funnel_paid_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='💳 Оплатить курс', callback_data='pay_course')],
    [InlineKeyboardButton(text='📞 Связаться с психологом', callback_data='contact_psychologist')],
    [InlineKeyboardButton(text='🔙 В главное меню', callback_data='back')]
]) 

free_paid_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Бесплатный')],
        [KeyboardButton(text='Платный')]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)