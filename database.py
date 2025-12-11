import asyncpg
from config import config
from typing import List, Dict, Any, Optional
import logging

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Подключение к базе данных с лимитами для Supabase"""
        try:
            # min_size=1, max_size=5 — оптимально для бесплатного тарифа Supabase и Render
            self.pool = await asyncpg.create_pool(
                config.DATABASE_URL,
                min_size=1,
                max_size=5
            )
            await self._create_tables()
            logging.info("✅ Успешное подключение к базе данных")
        except Exception as e:
            logging.error(f"❌ Критическая ошибка подключения к БД: {e}")
            raise e
    
    async def close(self):
        """Закрытие пула соединений (Graceful Shutdown)"""
        if self.pool:
            await self.pool.close()
            logging.info("💤 Соединение с БД закрыто")

    async def _create_tables(self):
        """Создание таблиц если они не существуют"""
        async with self.pool.acquire() as conn:
            # Таблица пользователей
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_active TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Таблица шаблонов
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(50) NOT NULL,
                    length INTEGER NOT NULL,
                    include_digits BOOLEAN DEFAULT FALSE,
                    include_lowercase BOOLEAN DEFAULT FALSE,
                    include_uppercase BOOLEAN DEFAULT FALSE,
                    include_special BOOLEAN DEFAULT FALSE,
                    exclude_similar BOOLEAN DEFAULT FALSE,
                    require_all_types BOOLEAN DEFAULT FALSE,
                    no_repeats BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id, name)
                )
            """)
            
            # Таблица последних параметров
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS last_params (
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE PRIMARY KEY,
                    length INTEGER NOT NULL,
                    include_digits BOOLEAN DEFAULT FALSE,
                    include_lowercase BOOLEAN DEFAULT FALSE,
                    include_uppercase BOOLEAN DEFAULT FALSE,
                    include_special BOOLEAN DEFAULT FALSE,
                    exclude_similar BOOLEAN DEFAULT FALSE,
                    require_all_types BOOLEAN DEFAULT FALSE,
                    no_repeats BOOLEAN DEFAULT FALSE,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
    
    async def get_or_create_user(self, telegram_id: int, username: str = None, 
                                 first_name: str = None, last_name: str = None):
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_id = $1",
                telegram_id
            )
            if not user:
                user = await conn.fetchrow(
                    """
                    INSERT INTO users (telegram_id, username, first_name, last_name)
                    VALUES ($1, $2, $3, $4)
                    RETURNING *
                    """,
                    telegram_id, username, first_name, last_name
                )
            else:
                await conn.execute(
                    "UPDATE users SET last_active = NOW(), username = $2 WHERE telegram_id = $1",
                    telegram_id, username
                )
            return user
    
    async def save_template(self, user_id: int, name: str, params: Dict[str, Any]) -> int:
        async with self.pool.acquire() as conn:
            template = await conn.fetchrow(
                """
                INSERT INTO templates 
                (user_id, name, length, include_digits, include_lowercase, 
                 include_uppercase, include_special, exclude_similar, 
                 require_all_types, no_repeats)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
                """,
                user_id, name,
                params['length'],
                params.get('include_digits', False),
                params.get('include_lowercase', False),
                params.get('include_uppercase', False),
                params.get('include_special', False),
                params.get('exclude_similar', False),
                params.get('require_all_types', False),
                params.get('no_repeats', False)
            )
            return template['id']
    
    async def get_user_templates(self, user_id: int) -> List[Dict]:
        async with self.pool.acquire() as conn:
            templates = await conn.fetch(
                "SELECT * FROM templates WHERE user_id = $1 ORDER BY created_at DESC",
                user_id
            )
            return [dict(t) for t in templates]
    
    async def get_template(self, template_id: int, user_id: int) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            template = await conn.fetchrow(
                "SELECT * FROM templates WHERE id = $1 AND user_id = $2",
                template_id, user_id
            )
            return dict(template) if template else None
    
    async def delete_template(self, template_id: int, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM templates WHERE id = $1 AND user_id = $2",
                template_id, user_id
            )
            return result.endswith("1")
    
    async def save_last_params(self, user_id: int, params: Dict[str, Any]):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO last_params 
                (user_id, length, include_digits, include_lowercase, 
                 include_uppercase, include_special, exclude_similar, 
                 require_all_types, no_repeats)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (user_id) DO UPDATE SET
                    length = EXCLUDED.length,
                    include_digits = EXCLUDED.include_digits,
                    include_lowercase = EXCLUDED.include_lowercase,
                    include_uppercase = EXCLUDED.include_uppercase,
                    include_special = EXCLUDED.include_special,
                    exclude_similar = EXCLUDED.exclude_similar,
                    require_all_types = EXCLUDED.require_all_types,
                    no_repeats = EXCLUDED.no_repeats,
                    updated_at = NOW()
                """,
                user_id,
                params['length'],
                params.get('include_digits', False),
                params.get('include_lowercase', False),
                params.get('include_uppercase', False),
                params.get('include_special', False),
                params.get('exclude_similar', False),
                params.get('require_all_types', False),
                params.get('no_repeats', False)
            )
    
    async def get_last_params(self, user_id: int) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            params = await conn.fetchrow(
                "SELECT * FROM last_params WHERE user_id = $1",
                user_id
            )
            return dict(params) if params else None

db = Database()