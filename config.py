import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")
    ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
    
    # Параметры генерации
    MIN_LENGTH = 4
    MAX_LENGTH = 50
    DEFAULT_LENGTHS = [8, 12, 16, 20, 24, 32]
    
    # Символы для генерации
    DIGITS = "0123456789"
    LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
    UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    SPECIAL = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Похожие символы для исключения
    SIMILAR_CHARS = {
        'l': '1', 'I': '1', '1': '1',
        'O': '0', '0': '0',
        'o': '0'
    }
    
    # Оценка надёжности
    SECURITY_LEVELS = {
        "very_low": ("🔴 Очень низкая", "Менее секунды"),
        "low": ("🟠 Низкая", "Несколько минут"),
        "medium": ("🟡 Средняя", "Дни/недели"),
        "high": ("🟢 Высокая", "Годы"),
        "very_high": ("🔵 Очень высокая", "Миллиарды лет")
    }

config = Config()