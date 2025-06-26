from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from filters.admin_filter import IsAdmin
from database.orm_query import get_or_create_broadcast_settings, update_default_broadcast_text
from utils.broadcast_utils import send_broadcast, format_broadcast_result
import keyboards.admin_kb as admin_kb

broadcast_router = Router()
broadcast_router.message.filter(IsAdmin())
broadcast_router.callback_query.filter(IsAdmin())

class BroadcastSettings(StatesGroup):
    waiting_for_default_text = State()
    waiting_for_custom_text = State()
    waiting_for_default_text_confirm = State()
    waiting_for_custom_confirm = State()

class SendVideo(StatesGroup):
    waiting_for_video = State()
    waiting_for_caption = State()
    waiting_for_confirm = State()

class SendVideoNote(StatesGroup):
    waiting_for_note = State()
    waiting_for_confirm = State()

@broadcast_router.callback_query(F.data=='broadcast_menu')
async def broadcast_menu(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    await callback.message.delete()
    await callback.answer('')
    await callback.message.answer('Выберите тип рассылки:', reply_markup=admin_kb.broadcast_menu.as_markup())


@broadcast_router.message(Command(commands='cancel'))
async def cancel_broadcast_settings(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer('Настройка рассылки отменена.', reply_markup=admin_kb.admin_kb.as_markup())
    else:
        await message.answer('Нет активного процесса настройки рассылки.')

@broadcast_router.callback_query(F.data=='send_all')
async def send_all_menu(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    await callback.answer('')
    
    # Получаем настройки рассылки админа
    settings = await get_or_create_broadcast_settings(session)
    
    await callback.message.answer(
        f'📢 <b>Настройка рассылки</b>\n\n'
        f'Текущий стандартный текст:\n'
        f'<i>"{settings.default_text}"</i>\n\n'
        f'Выберите тип рассылки:',
        reply_markup=admin_kb.broadcast_kb.as_markup()
    )

@broadcast_router.callback_query(F.data=='send_custom')
async def start_custom_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer('')
    await state.set_state(BroadcastSettings.waiting_for_custom_text)
    await callback.message.answer(
        '✏️ Введите текст для рассылки:\n\n'
        'Для отмены введите /cancel'
    )

@broadcast_router.callback_query(F.data=='change_default')
async def start_change_default(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer('')
    await state.set_state(BroadcastSettings.waiting_for_default_text)
    await callback.message.answer(
        '⚙️ Введите новый стандартный текст для рассылки:\n\n'
        'Для отмены введите /cancel'
    )

@broadcast_router.message(BroadcastSettings.waiting_for_custom_text)
async def get_custom_text(message: Message, state: FSMContext):
    custom_text = message.text
    await state.update_data(custom_text=custom_text)
    await state.set_state(BroadcastSettings.waiting_for_custom_confirm)
    await message.answer(
        f'Вы уверены, что хотите отправить этот текст всем пользователям?\n\n'
        f'<b>Текст:</b> {custom_text}\n\n',
        reply_markup=admin_kb.confirm_send_custom_text
    )

@broadcast_router.callback_query(F.data=='edit_custom_text', BroadcastSettings.waiting_for_custom_confirm)
async def edit_custom_text(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer('')
    await state.set_state(BroadcastSettings.waiting_for_custom_text)
    await callback.message.answer('Введите новый текст для рассылки:')

@broadcast_router.callback_query(F.data=='confirm_send_text', BroadcastSettings.waiting_for_custom_confirm)
async def confirm_send_text(callback: CallbackQuery, bot: Bot, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    custom_text = data.get('custom_text')
    await state.clear()
    success_count, failed_count = await send_broadcast(
        bot=bot,
        session=session,
        send_func=bot.send_message,
        content_type="кастомным текстом",
        text=custom_text
    )
    result_text = format_broadcast_result(success_count, failed_count, "кастомным текстом", custom_text)
    await callback.message.answer(result_text, reply_markup=admin_kb.admin_kb.as_markup())
    await callback.message.delete()
    await callback.answer('')

@broadcast_router.message(BroadcastSettings.waiting_for_default_text)
async def get_new_default_text(message: Message, state: FSMContext, session: AsyncSession):
    new_text = message.text
    await state.clear()
    
    # Обновляем стандартный текст
    await update_default_broadcast_text(session, new_text)
    
    await message.answer(
        f"✅ Стандартный текст обновлен!\n\n"
        f"📝 Новый текст: <i>\"{new_text}\"</i>\n\n"
        f"Теперь при выборе 'Стандартный текст' будет отправляться этот текст.",
        reply_markup=admin_kb.broadcast_kb.as_markup()
    )

@broadcast_router.callback_query(F.data=='send_default')
async def send_default_broadcast(callback: CallbackQuery, bot: Bot, session: AsyncSession, state: FSMContext):
    await callback.message.delete()
    await callback.answer('')
    await state.set_state(BroadcastSettings.waiting_for_default_text_confirm)
    # Получаем стандартный текст
    settings = await get_or_create_broadcast_settings(session)
    await state.update_data(default_text=settings.default_text)
    await callback.message.answer(
        f'Вы уверены, что хотите отправить этот текст всем пользователям?\n\n'
        f'<b>Текст:</b> {settings.default_text}\n\n',
        reply_markup=admin_kb.confirm_send_default_text
    )

@broadcast_router.callback_query(F.data=='confirm_send_text', BroadcastSettings.waiting_for_default_text_confirm)
async def confirm_send_text(callback: CallbackQuery, bot: Bot, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    default_text = data.get('default_text')
    await state.clear()
    success_count, failed_count = await send_broadcast(
        bot=bot,
        session=session,
        send_func=bot.send_message,
        content_type="стандартным текстом",
        text=default_text
    )
    result_text = format_broadcast_result(success_count, failed_count, "стандартным текстом", default_text)
    await callback.message.answer(result_text, reply_markup=admin_kb.admin_kb.as_markup())
    

@broadcast_router.callback_query(F.data=='send_video')
async def get_video(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer('')
    await state.clear()
    await state.set_state(SendVideo.waiting_for_video)
    await callback.message.answer('Отправьте видео для рассылки или отмените /cancel', reply_markup=admin_kb.back_to_admin.as_markup())

@broadcast_router.message(F.video, SendVideo.waiting_for_video)
async def receive_video(message: Message, state: FSMContext):
    video = message.video.file_id
    caption = message.caption 
    
    await state.update_data(video=video, caption=caption)
    await state.set_state(SendVideo.waiting_for_confirm)
    await message.answer(
    f"Вы уверены, что хотите отправить видео всем пользователям?\n\n"
    f"<b>Подпись:</b> {caption if caption else 'Без подписи'}\n\n",
    reply_markup=admin_kb.confirm_send_video
    )

@broadcast_router.callback_query(F.data=='edit_caption', SendVideo.waiting_for_confirm)
async def edit_caption(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer('')
    await state.set_state(SendVideo.waiting_for_caption)
    await callback.message.answer('Введите новый текст для подписи к видео:')


@broadcast_router.message(F.text, SendVideo.waiting_for_caption)
async def receive_caption(message: Message, state: FSMContext):
    caption = message.text
    await state.update_data(caption=caption)
    await state.set_state(SendVideo.waiting_for_confirm)
    await message.answer(
        f"Вы уверены, что хотите отправить видео всем пользователям?\n\n"
        f"<b>Подпись:</b> {caption}\n\n",
        reply_markup=admin_kb.confirm_send_video
    )


@broadcast_router.callback_query(F.data=='confirm_send_video', SendVideo.waiting_for_confirm)
async def broadcast_video_confirm(callback: CallbackQuery, bot: Bot, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    video = data.get('video')
    caption = data.get('caption')
    await state.clear()
    success_count, failed_count = await send_broadcast(
        bot=bot,
        session=session,
        send_func=bot.send_video,
        content_type="видео",
        video=video,
        caption=caption
    )
    # Формируем результат с дополнительной информацией о видео
    if success_count > 0 or failed_count > 0:
        result_text = (
            f"✅ Рассылка видео завершена!\n\n"
            f"📤 Отправлено: {success_count}\n"
            f"❌ Ошибок: {failed_count}\n\n"
            f"📝 Видео: <i>\"{video}\"</i>\n"
            f"📝 Подпись: {caption if caption else 'Без подписи'}"
        )
    else:
        result_text = "Список пользователей пуст"
    await callback.message.answer(result_text, reply_markup=admin_kb.admin_kb.as_markup())
    await callback.answer('')

@broadcast_router.callback_query(F.data=='send_video_note')
async def send_video_node(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer('')
    await state.set_state(SendVideoNote.waiting_for_note)
    await callback.message.answer('Отправьте кружок для рассылки или отмените /cancel', reply_markup=admin_kb.back_to_admin.as_markup())

@broadcast_router.message(F.video_note, SendVideoNote.waiting_for_note)
async def receive_video_note(message: Message, state: FSMContext):
    video_note = message.video_note.file_id
    await state.update_data(video_note=video_note)
    await state.set_state(SendVideoNote.waiting_for_confirm)
    await message.reply(
        f"Вы уверены, что хотите отправить кружок всем пользователям?\n\n"
        f"<b>Кружок:</b> {video_note}\n\n",
        reply_markup=admin_kb.confirm_send_video_note)

@broadcast_router.callback_query(F.data=='confirm_send_video_note', SendVideoNote.waiting_for_confirm)
async def broadcast_video_note_confirm(callback: CallbackQuery, bot: Bot, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    video_note = data.get('video_note')
    await state.clear()
    success_count, failed_count = await send_broadcast(
        bot=bot,
        session=session,
        send_func=bot.send_video_note,
        content_type="кружок",
        video_note=video_note
    )
    result_text = format_broadcast_result(success_count, failed_count, "кружок", video_note)
    await callback.message.answer(result_text, reply_markup=admin_kb.admin_kb.as_markup())
    await callback.message.delete()
    await callback.answer('')

