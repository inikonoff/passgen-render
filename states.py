from aiogram.fsm.state import State, StatesGroup

class PasswordStates(StatesGroup):
    # Основные состояния
    MAIN_MENU = State()
    SET_LENGTH = State()
    SET_CHAR_TYPES = State()
    SET_OPTIONS = State()
    PREVIEW = State()
    
    # Дополнительные состояния
    SAVE_TEMPLATE_NAME = State()
    IMPORT_TEMPLATE = State()
    
    # Управление шаблонами
    TEMPLATES_MENU = State()
    EDIT_TEMPLATE = State()
    DELETE_TEMPLATE = State()