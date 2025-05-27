from contextlib import asynccontextmanager
from config_data import config
import asyncpg

dbname = config.DB_NAME
user = config.DB_USER
password = config.DB_PASSWORD
host = config.DB_HOST


@asynccontextmanager
async def db_connection():
    """Контекстный менеджер для асинхронного подключения к базе данных."""
    conn = await asyncpg.connect(
        database=dbname, user=user, password=password, host=host
    )
    try:
        yield conn
    finally:
        await conn.close()


async def add_user(telegram_id):
    async with db_connection() as conn:
        sql = """CREATE TABLE IF NOT EXISTS users (telegram_id VARCHAR);"""
        await conn.execute(sql, )

        sql = (
            f"INSERT INTO public.users (telegram_id) "
            f"VALUES ($1)"
        )
        await conn.execute(sql, telegram_id)


async def all_users():
    async with db_connection() as conn:
        sql = """
            SELECT telegram_id
            FROM users
        """
        rows = await conn.fetch(sql, )
        if rows:
            return rows
