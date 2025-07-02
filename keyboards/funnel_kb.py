from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


# Клавиатуры для админа (управление воронками)
admin_funnel_kb = InlineKeyboardBuilder()
admin_funnel_kb.button(text='➕ Создать воронку', callback_data='create_funnel')
admin_funnel_kb.button(text='📋 Список воронок', callback_data='list_funnels')
admin_funnel_kb.button(text='📊 Статистика', callback_data='funnel_stats')
admin_funnel_kb.button(text='🔙 Назад', callback_data='back_to_admin')
admin_funnel_kb.adjust(2)

# Функция для создания клавиатуры выбора воронки
def get_funnel_selection_kb(funnels, action='select_funnel'):
    kb = InlineKeyboardBuilder()
    for funnel in funnels:
        if action == 'view_funnel':
            kb.button(text=f'📋 {funnel.name}', callback_data=f'view_funnel:{funnel.id}')
        elif action == 'stats_funnel':
            kb.button(text=f'📋 {funnel.name}', callback_data=f'stats_funnel:{funnel.id}')
        else:
            kb.button(text=f'📋 {funnel.name}', callback_data=f'select_funnel:{funnel.id}')
    kb.button(text='🔙 Назад', callback_data='manage_funnels')
    kb.adjust(1)
    return kb.as_markup()

# Функция для создания клавиатуры выбора курса для пользователей
def get_course_selection_kb(funnels):
    kb = InlineKeyboardBuilder()
    for funnel in funnels:
        kb.button(text=f'📚 {funnel.name}', callback_data=f'select_course:{funnel.id}')
    kb.button(text='🔙 В главное меню', callback_data='back')
    kb.adjust(1)
    return kb.as_markup()

# Клавиатура для управления конкретной воронкой
def get_funnel_manage_kb(funnel):
    funnel_manage_kb = InlineKeyboardBuilder()
    funnel_manage_kb.button(text='➕ Добавить этап', callback_data=f'add_funnel_step:{funnel.id}')
    funnel_manage_kb.button(text='📋 Этапы воронки', callback_data=f'view_funnel_steps:{funnel.id}')
    if funnel.is_active:
        funnel_manage_kb.button(text='🔄 Деактивировать воронку', callback_data=f'deactivate_funnel:{funnel.id}')
    else:
        funnel_manage_kb.button(text='🔄 Активировать воронку', callback_data=f'activate_funnel:{funnel.id}')
    funnel_manage_kb.button(text='❌ Удалить воронку', callback_data=f'delete_funnel:{funnel.id}')
    funnel_manage_kb.button(text='🔙 Назад', callback_data='manage_funnels')
    funnel_manage_kb.adjust(2)
    return funnel_manage_kb.as_markup()
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

# Клавиатура для платных этапов (когда прохождение останавливается)
funnel_paid_stop_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='💼 Записаться', callback_data='service_list')],
    [InlineKeyboardButton(text='📚 Дополнительные материалы', callback_data='more_materials')],
    [InlineKeyboardButton(text='🔄 Начать курс заново', callback_data='restart_course')],
    [InlineKeyboardButton(text='🔙 В главное меню', callback_data='back')]
])

funnel_complete_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='💼 Записаться', callback_data='service_list')],
    [InlineKeyboardButton(text='📚 Дополнительные материалы', callback_data='more_materials')],
    [InlineKeyboardButton(text='🔙 В главное меню', callback_data='back')]
])

# Клавиатура для продолжения после платного этапа
funnel_continue_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='💼 Записаться на консультацию', callback_data='service_list')],
    [InlineKeyboardButton(text='📞 Связаться с психологом', callback_data='consultation_request')],
    [InlineKeyboardButton(text='📚 Дополнительные материалы', callback_data='more_materials')],
    [InlineKeyboardButton(text='🔙 В главное меню', callback_data='back')]
])

# Устаревшие клавиатуры (оставляем для совместимости)
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