from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any

def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Новый пароль", callback_data="new_password"),
        InlineKeyboardButton(text="📁 Мои шаблоны", callback_data="my_templates")
    )
    builder.row(
        InlineKeyboardButton(text="⚡ Последние параметры", callback_data="last_params"),
        InlineKeyboardButton(text="ℹ️ Справка", callback_data="help")
    )
    return builder.as_markup()

def length_kb() -> InlineKeyboardMarkup:
    """Выбор длины пароля"""
    builder = InlineKeyboardBuilder()
    buttons = [
        InlineKeyboardButton(text="8", callback_data="length_8"),
        InlineKeyboardButton(text="12", callback_data="length_12"),
        InlineKeyboardButton(text="16", callback_data="length_16"),
        InlineKeyboardButton(text="20", callback_data="length_20"),
        InlineKeyboardButton(text="24", callback_data="length_24"),
        InlineKeyboardButton(text="32", callback_data="length_32"),
    ]
    for i in range(0, len(buttons), 3):
        builder.row(*buttons[i:i+3])
    builder.row(InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="custom_length"))
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main"))
    return builder.as_markup()

def char_types_kb(current_types: Dict[str, bool] = None) -> InlineKeyboardMarkup:
    """Выбор типов символов (Только статус + текст)"""
    if current_types is None:
        current_types = {
            'digits': False,
            'lowercase': False,
            'uppercase': False,
            'special': False
        }
    
    builder = InlineKeyboardBuilder()
    
    # Убрали все лишние иконки из кортежей
    types_config = [
        ('digits', 'Цифры (0-9)'),
        ('lowercase', 'Строчные буквы (a-z)'),
        ('uppercase', 'Заглавные буквы (A-Z)'),
        ('special', 'Спецсимволы (!@#$)'),
    ]
    
    for key, text in types_config:
        # Логика простая: Если True -> ✅, Если False -> ❌
        status = "✅" if current_types.get(key, False) else "❌"
        builder.row(InlineKeyboardButton(
            text=f"{status} {text}",
            callback_data=f"toggle_{key}"
        ))
    
    builder.row(
        InlineKeyboardButton(text="➡️ Далее", callback_data="to_options"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_length")
    )
    
    return builder.as_markup()

def options_kb(current_options: Dict[str, bool] = None) -> InlineKeyboardMarkup:
    """Дополнительные опции (Только статус + текст)"""
    if current_options is None:
        current_options = {
            'exclude_similar': False,
            'require_all_types': False,
            'no_repeats': False
        }
    
    builder = InlineKeyboardBuilder()
    
    # Полностью убрали иконки (👁️, ✅, 🔄) из названий
    options_config = [
        ('exclude_similar', 'Исключить похожие символы (l/1, O/0)'),
        ('require_all_types', 'Обязательно все выбранные типы'),
        ('no_repeats', 'Без повторяющихся символов'),
    ]
    
    for key, text in options_config:
        # Логика простая: Если True -> ✅, Если False -> ❌
        status = "✅" if current_options.get(key, False) else "❌"
        builder.row(InlineKeyboardButton(
            text=f"{status} {text}",
            callback_data=f"option_{key}"
        ))
    
    builder.row(
        InlineKeyboardButton(text="➡️ Предпросмотр", callback_data="to_preview"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_chars")
    )
    
    return builder.as_markup()

def preview_kb() -> InlineKeyboardMarkup:
    """Предпросмотр параметров"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Сгенерировать", callback_data="generate"),
        InlineKeyboardButton(text="💾 Сохранить шаблон", callback_data="save_template")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data="back_to_options"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_main")
    )
    return builder.as_markup()

def templates_kb(templates: List[Dict]) -> InlineKeyboardMarkup:
    """Список шаблонов"""
    builder = InlineKeyboardBuilder()
    
    for template in templates:
        builder.row(InlineKeyboardButton(
            text=f"📝 {template['name']} ({template['length']} симв.)",
            callback_data=f"template_{template['id']}"
        ))
    
    builder.row(
        InlineKeyboardButton(text="➕ Новый шаблон", callback_data="new_template"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main")
    )
    
    return builder.as_markup()

def template_actions_kb(template_id: int) -> InlineKeyboardMarkup:
    """Действия с шаблоном"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Использовать", callback_data=f"use_template_{template_id}"),
        InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"rename_template_{template_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_template_{template_id}"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_templates")
    )
    return builder.as_markup()

def generated_kb() -> InlineKeyboardMarkup:
    """После генерации пароля"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Ещё один", callback_data="generate_another"),
        InlineKeyboardButton(text="⚙️ Изменить параметры", callback_data="edit_params")
    )
    builder.row(
        InlineKeyboardButton(text="💾 Сохранить шаблон", callback_data="save_current"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_main")
    )
    return builder.as_markup()

def back_to_main_kb() -> InlineKeyboardMarkup:
    """Кнопка назад в меню"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_main"))
    return builder.as_markup()

def help_kb() -> InlineKeyboardMarkup:
    """Клавиатура для справки"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔄 Новый пароль", callback_data="new_password"))
    builder.row(InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_main"))
    return builder.as_markup()
