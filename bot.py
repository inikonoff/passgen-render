import asyncio
import random
import math
import logging
import os
from aiohttp import web
from typing import Dict, Any, Tuple
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from states import PasswordStates
from keyboards import (
    main_menu_kb, length_kb, char_types_kb, options_kb,
    preview_kb, templates_kb, template_actions_kb,
    generated_kb, back_to_main_kb, help_kb
)
from database import db

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- DEBUG START ---
print("--- ОТЛАДКА ТОКЕНА ---")
token = config.BOT_TOKEN
if not token:
    print("❌ Токен пустой! (None или Empty String)")
else:
    print(f"✅ Длина токена: {len(token)}")
    print(f"👀 Первые 5 символов: '{token[:5]}'")
    print(f"👀 Последние 5 символов: '{token[-5:]}'")
    # Проверка на кавычки
    if token.startswith('"') or token.startswith("'"):
        print("🚨 ВНИМАНИЕ: Токен начинается с кавычки! Удалите кавычки в Render!")
    if " " in token:
        print("🚨 ВНИМАНИЕ: В токене есть пробелы! Удалите их!")
print("----------------------")
# --- DEBUG END ---

# Инициализация
router = Router()
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

# === ЛОГИКА ГЕНЕРАТОРА ===
class PasswordGenerator:
    """Генератор паролей"""
    
    @staticmethod
    def get_alphabet(params: Dict[str, Any]) -> str:
        """Получить алфавит на основе параметров"""
        alphabet = ""
        
        if params.get('include_digits'):
            alphabet += config.DIGITS
        if params.get('include_lowercase'):
            alphabet += config.LOWERCASE
        if params.get('include_uppercase'):
            alphabet += config.UPPERCASE
        if params.get('include_special'):
            alphabet += config.SPECIAL
        
        if params.get('exclude_similar'):
            for char, replace in config.SIMILAR_CHARS.items():
                alphabet = alphabet.replace(char, '')
        
        return alphabet
    
    @staticmethod
    def generate_password(params: Dict[str, Any]) -> str:
        """Оптимизированная генерация пароля"""
        length = params['length']
        alphabet = PasswordGenerator.get_alphabet(params)
        
        if not alphabet:
            raise ValueError("Алфавит пустой. Выберите хотя бы один тип символов.")
        
        if params.get('no_repeats') and len(alphabet) < length:
            raise ValueError(f"Невозможно сгенерировать пароль без повторов: "
                           f"алфавит ({len(alphabet)}) меньше длины ({length})")
        
        password_chars = []
        
        # Если обязательно нужны все типы
        if params.get('require_all_types'):
            required_groups = []
            if params.get('include_digits'): required_groups.append(config.DIGITS)
            if params.get('include_lowercase'): required_groups.append(config.LOWERCASE)
            if params.get('include_uppercase'): required_groups.append(config.UPPERCASE)
            if params.get('include_special'): required_groups.append(config.SPECIAL)
            
            for group in required_groups:
                if params.get('exclude_similar'):
                    group = ''.join([c for c in group if c not in config.SIMILAR_CHARS])
                
                if group:
                    char = random.choice(group)
                    password_chars.append(char)
                    if params.get('no_repeats'):
                        alphabet = alphabet.replace(char, '', 1)

        # Дозаполняем остаток
        remaining_length = length - len(password_chars)
        
        if remaining_length > 0:
            if params.get('no_repeats'):
                password_chars.extend(random.sample(alphabet, remaining_length))
            else:
                password_chars.extend(random.choices(alphabet, k=remaining_length))
        
        random.shuffle(password_chars)
        return ''.join(password_chars)
    
    @staticmethod
    def calculate_security(params: Dict[str, Any]) -> Tuple[str, str, float]:
        """Рассчитать безопасность пароля"""
        alphabet = PasswordGenerator.get_alphabet(params)
        alphabet_size = len(alphabet)
        length = params['length']
        
        if params.get('no_repeats'):
            if alphabet_size < length:
                combinations = 0
            else:
                combinations = math.prod(range(alphabet_size - length + 1, alphabet_size + 1))
        else:
            combinations = alphabet_size ** length
        
        if combinations < 10**6:
            level = "very_low"
        elif combinations < 10**12:
            level = "low"
        elif combinations < 10**18:
            level = "medium"
        elif combinations < 10**24:
            level = "high"
        else:
            level = "very_high"
        
        security_name, time_estimate = config.SECURITY_LEVELS[level]
        return security_name, time_estimate, combinations

# ========== HANDLERS (Обработчики команд) ==========

@router.callback_query(F.data.startswith("option_"))
async def toggle_option(callback: CallbackQuery, state: FSMContext):
    # Исправление: убираем префикс "option_" целиком, чтобы сохранить хвост с подчеркиваниями
    option = callback.data.replace("option_", "")
    
    data = await state.get_data()
    # Получаем текущие настройки или создаем пустые по умолчанию
    options = data.get('options', {
        'exclude_similar': False, 
        'require_all_types': False, 
        'no_repeats': False
    })
    
    # Переключаем значение (True <-> False)
    options[option] = not options.get(option, False)
    
    await state.update_data(options=options)
    await callback.message.edit_reply_markup(reply_markup=options_kb(options))
    await callback.answer()

async def show_help(message: Message):
    help_text = (
        "📚 *Справка по генератору паролей*\n\n"
        "🔐 *Как работает:*\n"
        "1. Выберите длину пароля (4-50 символов)\n"
        "2. Выберите типы символов\n"
        "3. Настройте дополнительные опции\n"
        "4. Просмотрите параметры и сгенерируйте\n\n"
        "💡 *Совет:*\n"
        "Используйте менеджер паролей и включайте двухфакторную аутентификацию."
    )
    await message.answer(help_text, reply_markup=help_kb(), parse_mode="Markdown")

# ========== MAIN MENU ==========

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(PasswordStates.MAIN_MENU)
    await callback.message.edit_text(
        "🔐 *Главное меню*\n\nВыберите действие:",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "new_password")
async def new_password(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PasswordStates.SET_LENGTH)
    await callback.message.edit_text(
        "📏 *Шаг 1: Длина пароля*\n\n"
        "Выберите длину пароля или введите число от 4 до 50:",
        reply_markup=length_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "last_params")
async def last_params(callback: CallbackQuery, state: FSMContext):
    user_id = (await db.get_or_create_user(callback.from_user.id))['id']
    last_params_data = await db.get_last_params(user_id)
    
    if not last_params_data:
        await callback.answer("❌ У вас нет сохраненных параметров", show_alert=True)
        return
    
    params = {
        'length': last_params_data['length'],
        'include_digits': last_params_data['include_digits'],
        'include_lowercase': last_params_data['include_lowercase'],
        'include_uppercase': last_params_data['include_uppercase'],
        'include_special': last_params_data['include_special'],
        'exclude_similar': last_params_data['exclude_similar'],
        'require_all_types': last_params_data['require_all_types'],
        'no_repeats': last_params_data['no_repeats']
    }
    
    await state.update_data(params=params)
    await generate_and_send_password(callback.message, params, state)
    await callback.answer()

@router.callback_query(F.data == "my_templates")
async def my_templates(callback: CallbackQuery, state: FSMContext):
    user_id = (await db.get_or_create_user(callback.from_user.id))['id']
    templates = await db.get_user_templates(user_id)
    
    if not templates:
        await callback.message.edit_text(
            "📁 *Мои шаблоны*\n\n"
            "У вас пока нет сохраненных шаблонов.",
            reply_markup=back_to_main_kb(),
            parse_mode="Markdown"
        )
    else:
        await state.set_state(PasswordStates.TEMPLATES_MENU)
        await callback.message.edit_text(
            "📁 *Мои шаблоны*\n\n"
            "Выберите шаблон для использования:",
            reply_markup=templates_kb(templates),
            parse_mode="Markdown"
        )
    await callback.answer()

# ========== LENGTH SELECTION ==========

@router.callback_query(F.data.startswith("length_"))
async def set_length(callback: CallbackQuery, state: FSMContext):
    length = int(callback.data.split("_")[1])
    await state.update_data(length=length)
    await state.set_state(PasswordStates.SET_CHAR_TYPES)
    
    await callback.message.edit_text(
        "🔠 *Шаг 2: Типы символов*\n\n"
        "Выберите какие символы использовать в пароле:",
        reply_markup=char_types_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "custom_length")
async def custom_length(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✏️ *Введите длину пароля*\n\n"
        f"Число от {config.MIN_LENGTH} до {config.MAX_LENGTH}:",
        reply_markup=back_to_main_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(PasswordStates.SET_LENGTH)
async def process_custom_length(message: Message, state: FSMContext):
    try:
        length = int(message.text)
        if length < config.MIN_LENGTH or length > config.MAX_LENGTH:
            await message.answer(
                f"❌ Длина должна быть от {config.MIN_LENGTH} до {config.MAX_LENGTH}",
                reply_markup=back_to_main_kb()
            )
            return
        
        await state.update_data(length=length)
        await state.set_state(PasswordStates.SET_CHAR_TYPES)
        await message.answer(
            "🔠 *Шаг 2: Типы символов*\n\nВыберите символы:",
            reply_markup=char_types_kb()
        )
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число", reply_markup=back_to_main_kb())

# ========== CHAR TYPES ==========

@router.callback_query(F.data.startswith("toggle_"))
async def toggle_char_type(callback: CallbackQuery, state: FSMContext):
    char_type = callback.data.split("_")[1]
    data = await state.get_data()
    char_types = data.get('char_types', {'digits': False, 'lowercase': False, 'uppercase': False, 'special': False})
    char_types[char_type] = not char_types.get(char_type, False)
    await state.update_data(char_types=char_types)
    await callback.message.edit_reply_markup(reply_markup=char_types_kb(char_types))
    await callback.answer()

@router.callback_query(F.data == "to_options")
async def to_options(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    char_types = data.get('char_types', {})
    if not any(char_types.values()):
        await callback.answer("❌ Выберите хотя бы один тип символов", show_alert=True)
        return
    
    await state.update_data(
        include_digits=char_types.get('digits', False),
        include_lowercase=char_types.get('lowercase', False),
        include_uppercase=char_types.get('uppercase', False),
        include_special=char_types.get('special', False)
    )
    await state.set_state(PasswordStates.SET_OPTIONS)
    await callback.message.edit_text(
        "⚙️ *Шаг 3: Дополнительные опции*",
        reply_markup=options_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ========== OPTIONS ==========

@router.callback_query(F.data.startswith("option_"))
async def toggle_option(callback: CallbackQuery, state: FSMContext):
    option = callback.data.split("_")[1]
    data = await state.get_data()
    options = data.get('options', {'exclude_similar': False, 'require_all_types': False, 'no_repeats': False})
    options[option] = not options.get(option, False)
    await state.update_data(options=options)
    await callback.message.edit_reply_markup(reply_markup=options_kb(options))
    await callback.answer()

@router.callback_query(F.data == "to_preview")
async def to_preview(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    options = data.get('options', {})
    await state.update_data(
        exclude_similar=options.get('exclude_similar', False),
        require_all_types=options.get('require_all_types', False),
        no_repeats=options.get('no_repeats', False)
    )
    await state.set_state(PasswordStates.PREVIEW)
    
    params = {
        'length': data.get('length', 12),
        'include_digits': data.get('include_digits', False),
        'include_lowercase': data.get('include_lowercase', False),
        'include_uppercase': data.get('include_uppercase', False),
        'include_special': data.get('include_special', False),
        'exclude_similar': options.get('exclude_similar', False),
        'require_all_types': options.get('require_all_types', False),
        'no_repeats': options.get('no_repeats', False)
    }
    await state.update_data(params=params)
    await callback.message.edit_text(
        get_preview_text(params),
        reply_markup=preview_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

def get_preview_text(params: Dict[str, Any]) -> str:
    security_name, time_estimate, combinations = PasswordGenerator.calculate_security(params)
    
    if combinations >= 10**24: combs = f"{combinations / 10**24:.1f}×10²⁴"
    elif combinations >= 10**6: combs = f"{combinations / 10**6:.1f}×10⁶"
    else: combs = f"{combinations:,}"
    
    return (
        f"📊 *Предпросмотр параметров*\n\n"
        f"• **Длина:** {params['length']} символов\n"
        f"• **Оценка безопасности:** {security_name}\n"
        f"• **Комбинации:** {combs}\n"
        f"• **Время подбора:** ~{time_estimate}\n\n"
        f"*Сгенерировать пароль?*"
    )

# ========== GENERATION ==========

@router.callback_query(F.data == "generate")
async def generate_password(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    params = data.get('params', {})
    try:
        await generate_and_send_password(callback.message, params, state)
    except ValueError as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
    except Exception as e:
        logger.error(f"Generate error: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)
    await callback.answer()

async def generate_and_send_password(message: Message, params: Dict[str, Any], state: FSMContext):
    password = PasswordGenerator.generate_password(params)
    user_id = (await db.get_or_create_user(message.chat.id))['id']
    await db.save_last_params(user_id, params)
    await state.update_data(params=params)
    
    await message.bot.send_message(message.chat.id, f"`{password}`", parse_mode="Markdown")
    
    security_name, _, _ = PasswordGenerator.calculate_security(params)
    await message.bot.send_message(
        chat_id=message.chat.id,
        text=f"🔐 Пароль готов!\nНадёжность: {security_name}",
        reply_markup=generated_kb(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "generate_another")
async def generate_another(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    params = data.get('params', {})
    if not params:
        await callback.answer("❌ Нет параметров", show_alert=True)
        return
    
    try:
        await generate_and_send_password(callback.message, params, state)
    except ValueError as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
    await callback.answer()

@router.callback_query(F.data == "edit_params")
async def edit_params(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PasswordStates.SET_LENGTH)
    await callback.message.edit_text(
        f"📏 *Изменить длину пароля*\n\nВыберите новую длину:",
        reply_markup=length_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ========== TEMPLATES (Save/Load) ==========

@router.callback_query(F.data == "save_template")
async def save_template_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PasswordStates.SAVE_TEMPLATE_NAME)
    await callback.message.edit_text(
        "💾 *Сохранение шаблона*\n\nВведите название (до 50 символов):",
        reply_markup=back_to_main_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(PasswordStates.SAVE_TEMPLATE_NAME)
async def save_template_finish(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name or len(name) > 50:
        await message.answer("❌ Название должно быть от 1 до 50 символов", reply_markup=back_to_main_kb())
        return
    
    data = await state.get_data()
    params = data.get('params', {})
    if not params:
        await message.answer("❌ Нет параметров для сохранения", reply_markup=back_to_main_kb())
        return
    
    user_id = (await db.get_or_create_user(message.from_user.id))['id']
    try:
        await db.save_template(user_id, name, params)
        await message.answer(f"✅ Шаблон '{name}' сохранен!", reply_markup=main_menu_kb())
        await state.set_state(PasswordStates.MAIN_MENU)
    except Exception as e:
        if "duplicate key" in str(e).lower():
            await message.answer("❌ Шаблон с таким названием уже существует", reply_markup=back_to_main_kb())
        else:
            logger.error(f"Template save error: {e}")
            await message.answer("❌ Ошибка при сохранении", reply_markup=back_to_main_kb())

@router.callback_query(F.data.startswith("template_"))
async def template_selected(callback: CallbackQuery, state: FSMContext):
    t_id = int(callback.data.split("_")[1])
    user_id = (await db.get_or_create_user(callback.from_user.id))['id']
    template = await db.get_template(t_id, user_id)
    
    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"📝 *Шаблон: {template['name']}*\n\nВыберите действие:",
        reply_markup=template_actions_kb(t_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("use_template_"))
async def use_template(callback: CallbackQuery, state: FSMContext):
    t_id = int(callback.data.split("_")[2])
    user_id = (await db.get_or_create_user(callback.from_user.id))['id']
    template = await db.get_template(t_id, user_id)
    
    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return
    
    params = {
        'length': template['length'],
        'include_digits': template['include_digits'],
        'include_lowercase': template['include_lowercase'],
        'include_uppercase': template['include_uppercase'],
        'include_special': template['include_special'],
        'exclude_similar': template['exclude_similar'],
        'require_all_types': template['require_all_types'],
        'no_repeats': template['no_repeats']
    }
    await state.update_data(params=params)
    await generate_and_send_password(callback.message, params, state)
    await callback.answer()

@router.callback_query(F.data.startswith("delete_template_"))
async def delete_template(callback: CallbackQuery):
    t_id = int(callback.data.split("_")[2])
    user_id = (await db.get_or_create_user(callback.from_user.id))['id']
    await db.delete_template(t_id, user_id)
    
    templates = await db.get_user_templates(user_id)
    if not templates:
        await callback.message.edit_text("✅ Шаблон удален! Шаблонов больше нет.", reply_markup=back_to_main_kb())
    else:
        await callback.message.edit_text("✅ Шаблон удален! Выберите другой:", reply_markup=templates_kb(templates))
    await callback.answer()

# ========== NAVIGATION BACK ==========

@router.callback_query(F.data == "back_to_length")
async def back_to_length(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PasswordStates.SET_LENGTH)
    await callback.message.edit_text("📏 *Шаг 1: Длина пароля*", reply_markup=length_kb(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "back_to_chars")
async def back_to_chars(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PasswordStates.SET_CHAR_TYPES)
    data = await state.get_data()
    char_types = {
        'digits': data.get('include_digits', False),
        'lowercase': data.get('include_lowercase', False),
        'uppercase': data.get('include_uppercase', False),
        'special': data.get('include_special', False)
    }
    await callback.message.edit_text("🔠 *Шаг 2: Типы символов*", reply_markup=char_types_kb(char_types), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "back_to_options")
async def back_to_options(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PasswordStates.SET_OPTIONS)
    data = await state.get_data()
    options = {
        'exclude_similar': data.get('exclude_similar', False),
        'require_all_types': data.get('require_all_types', False),
        'no_repeats': data.get('no_repeats', False)
    }
    await callback.message.edit_text("⚙️ *Шаг 3: Дополнительные опции*", reply_markup=options_kb(options), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "back_to_templates")
async def back_to_templates(callback: CallbackQuery, state: FSMContext):
    await my_templates(callback, state)

# ========== ADMIN COMMANDS ==========

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id not in config.ADMIN_IDS: return
    async with db.pool.acquire() as conn:
        stats = await conn.fetchrow("SELECT COUNT(*) as u, COUNT(DISTINCT DATE(created_at)) as d FROM users")
    await message.answer(f"📊 *Статистика*\nПользователей: {stats['u']}\nДней работы: {stats['d']}", parse_mode="Markdown")

# === ВЕБ-СЕРВЕР ДЛЯ RENDER (Health Check) ===

async def health_check(request):
    """Простой ответ на пинг"""
    return web.Response(text="I'm alive! Bot is running.")

async def start_web_server():
    """Запуск веб-сервера в фоне"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"🌐 Веб-сервер запущен на порту {port}")

# === MAIN EXECUTION ===

async def on_shutdown(dispatcher: Dispatcher):
    logging.warning("🛑 Бот останавливается...")
    await db.close()

async def main():
    logging.info("🚀 Запуск бота...")
    
    try:
        await db.connect()
    except Exception:
        logging.critical("Не удалось подключиться к БД. Выход.")
        return

    dp.shutdown.register(on_shutdown)
    
    # Запускаем веб-сервер
    await start_web_server()
    
    # Запускаем бота
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка polling: {e}")

if __name__ == "__main__":
    asyncio.run(main())
