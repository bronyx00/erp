import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# --- IMPORTACIÓN DINÁMICA DE MODELOS ---
# Esto funciona para todos tus servicios porque todos tienen la estructura app.models
from app.models import Base 

config = context.config

# Configurar logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Asignar los metadatos de tus modelos para que Alembic detecte los cambios
target_metadata = Base.metadata

# Leer la URL de la base de datos desde la variable de entorno de Docker
# Si falla, usa una por defecto (útil para pruebas locales fuera de Docker)
DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://admin:admin@localhost:5432/finance_db")
config.set_main_option("sqlalchemy.url", DB_URL)

def run_migrations_offline() -> None:
    """Corre migraciones en modo 'offline'."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    """Helper para correr migraciones síncronas en contexto asíncrono."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Corre migraciones en modo 'online'."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())