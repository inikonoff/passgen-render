import asyncio
import random
import math
import logging
import os  # Добавили для чтения PORT из переменных окружения
from aiohttp import web  # Добавили для веб-сервера
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

# Инициализация
router = Router()
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

# === ЛОГИКА ГЕНЕРАТОРА (Свернута для краткости, она не менялась) ===
class PasswordGenerator:
    """Генератор паролей"""
    @staticmethod
    def get_alphabet(params: Dict[str, Any]) -> str:
        alphabet = ""
        if params.get('include_digits'): alphabet += config.DIGITS
        if params.get('include_lowercase'): alphabet += config.LOWERCASE
        if params.get('include_uppercase'): alphabet += config.UPPERCASE
        if params.get('include_special'): alphabet += config.SPECIAL
        if params.get('exclude_similar'):
            for char, replace in config.SIMILAR_CHARS.items():
                alphabet = alphabet.replace(char, '')
        return alphabet
    
    @staticmethod
    def generate_password(params: Dict[str, Any]) -> str:
        length = params['length']
        alphabet = PasswordGenerator.get_alphabet(params)
        
        if not alphabet: raise ValueError("Алфавит пустой.")
        if params.get('no_repeats') and len(alphabet) < length:
            raise ValueError(f"Алфавит ({len(alphabet)}) меньше длины ({length})")
        
        password_chars = []
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
                    if params.get('no_repeats'): alphabet = alphabet.replace(char, '', 1)

        remaining = length - len(password_chars)
        if remaining > 0:
            if params.get('no_repeats'): password_chars.extend(random.sample(alphabet, remaining))
            else: password_chars.extend(random.choices(alphabet, k=remaining))
        
        random.shuffle(password_chars)
        return ''.join(password_chars)
    
    @staticmethod
    def calculate_security(params: Dict[str, Any]) -> Tuple[str, str, float]:
        alphabet = PasswordGenerator.get_alphabet(params)
        size = len(alphabet)
        length = params['length']
        if params.get('no_repeats'):
            if size < length: combs = 0 
            else: combs = math.prod(range(size - length + 1, size + 1))
        else: combs = size ** length
        
        if combs < 10**6: level = "very_low"
        elif combs < 10**12: level = "low"
        elif combs < 10**18: level = "medium"
        elif combs < 10**24: level = "high"
        else: level = "very_high"
        
        sec, time = config.SECURITY_LEVELS[level]
        return sec, time, combs

# === ХЕНДЛЕРЫ (Оставлены без изменений) ===
# ... (код хендлеров остается таким же, как в предыдущем ответе) ...
# Я их не дублирую здесь, чтобы не загромождать ответ, 
# просто вставьте сюда все функции от @router.message(CommandStart()) до @router.message(Command("stats"))
# Если нужно, я могу продублировать полный файл, но логика хендлеров не меняется.

# ВСТАВЬТЕ СЮДА ВЕСЬ КОД ХЕНДЛЕРОВ ИЗ ПРЕДЫДУЩЕГО ОТВЕТА

# === ВЕБ-СЕРВЕР ДЛЯ RENDER (Health Check) ===

async def health_check(request):
    """Простой ответ на пинг"""
    return web.Response(text="I'm alive! Bot is running.")

async def start_web_server():
    """Запуск веб-сервера в фоне"""
    app = web.Application()
    app.router.add_get('/', health_check)  # Маршрут для главной страницы
    app.router.add_get('/health', health_check) # Маршрут для /health
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render передает порт через переменную окружения PORT
    # Если переменной нет (локально), используем 8080
    port = int(os.environ.get("PORT", 8080))
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"🌐 Веб-сервер запущен на порту {port}")

# === MAIN ===

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
    
    # Сначала запускаем веб-сервер
    await start_web_server()
    
    # Затем запускаем бота
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка polling: {e}")

if __name__ == "__main__":
    asyncio.run(main())
