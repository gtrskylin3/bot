from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, Contact, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import get_or_create_user, check_user_phone, update_phone
from keyboards import user_kb
from .funnel_user_router import Register
import phonenumbers

user_profile_router = Router()

class UserProfile(StatesGroup):
    waiting_for_phone = State()

@user_profile_router.callback_query(F.data=="user_profile")
async def user_profile(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    if not user.phone:
        await state.set_state(Register.waiting_for_phone)
        await callback.message.answer("<b>Регистрация</b>\n\n"
                                      "📞 Введите ваш номер телефона:\n"
                                    "<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>\n\n"
                                    "<i>Отправте свой номер в чат</i>\n<i>Или поделитесь контктом нажав на кнопку</i>\n"
                                    "<b>После регистрации вы сможете проходить курсы в боте и записываться на услуги</b>\n\n"
                                    "<i>Для отмены записи введите /cancel</i>",
                                    
                                      reply_markup=user_kb.contact_kb)
        await callback.answer('')
        return

    await callback.message.answer(f"👤 <b>Профиль пользователя</b>\n\n"
                                  f"<b>Имя:</b> {user.name}\n"
                                  f"<b>Телефон:</b> {user.phone}\n"
                                  "<i>Для изменения номера телефона нажмите кнопку ниже</i>", reply_markup=user_kb.user_profile_kb.as_markup())
    await callback.answer('')
@user_profile_router.callback_query(StateFilter(None), F.data=="change_user_phone")
async def change_user_phone(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    await callback.message.delete()
    await state.set_state(UserProfile.waiting_for_phone)
    await callback.message.answer("📞 Введите ваш новый номер телефона:\n\n"
                                  "<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>\n\n"
                                  "<i>Или нажмите кнопку ниже, чтобы поделиться контактом</i>\n\n"
                                  "<i>Для отмены введите /cancel</i>", reply_markup=user_kb.contact_kb)


@user_profile_router.message(UserProfile.waiting_for_phone, Command('cancel'))
async def cancel_signup(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state and (current_state.startswith("UserProfile") or current_state.startswith("Register")):
        await state.clear()
        await message.answer(
            "Изменение номера <b>отменено</b>",
            reply_markup=user_kb.user_profile_kb.as_markup()
        )
        await message.answer(
            "Вы всегда можете его изменить в своем <b>профиле</b>",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer("Нет активной записи для отмены", reply_markup=ReplyKeyboardRemove())


@user_profile_router.message(UserProfile.waiting_for_phone)
async def update_phone_handler(message: Message, state: FSMContext, session: AsyncSession):
    if message.contact:
        contact: Contact = message.contact
        # Сохраняем данные контакта
        phone=contact.phone_number
        if phone.startswith('8') or phone.startswith('7'):
            phone = '+7' + phone[1:]
        await update_phone(session, message.from_user.id, phone)
        await state.clear()
        await message.answer(f"<i>Ваш новый номер телефона:</i> <b>{phone}</b>",
        reply_markup=ReplyKeyboardRemove()
        )
        await message.answer("✅ Номер телефона успешно обновлен!", reply_markup=user_kb.user_profile_kb.as_markup()) 
    else:
        phone = message.text.strip()
        if phone.startswith('8'):
            phone = '+7' + phone[1:]
        phone = phone.replace(' ', '')
        try:
            parsed_phone = phonenumbers.parse(phone, "RU")
            if not phonenumbers.is_valid_number(parsed_phone):
                await message.answer("❌ Неверный формат номера телефона. Попробуйте снова:\n\n<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>")
                return
            await update_phone(session, message.from_user.id, phone)
            await state.clear()
            await message.answer(f"<i>Ваш новый номер телефона:</i> <b>{phone}</b>",
            reply_markup=ReplyKeyboardRemove()
            )
            await message.answer("✅ Номер телефона успешно обновлен!", reply_markup=user_kb.user_profile_kb.as_markup()) 
            #валидация телефона
        except phonenumbers.NumberParseException:
            await message.answer("❌ Неверный формат номера телефона. Попробуйте снова:\n\n<i>Формат: +7XXXXXXXXXX или 8XXXXXXXXXX</i>")
            return

