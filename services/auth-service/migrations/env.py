import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 1. IMPORTA TUS MODELOS AQUÍ
# Esto es vital para que Alembic detecte tus tablas
from app.models import Base 
# Asegúrate que 'app.models' sea accesible. Como el dockerfile pone 'app' en el path, esto debería funcionar.

config = context.config

# Configurar logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 2. Asignar Metadatos de tus Modelos
target_metadata = Base.metadata

# 3. Obtener URL desde Variable de Entorno (Igual que en database.py)
# Si no existe (ej. local fuera de docker), usa un fallback
DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://admin:admin@localhost:5432/auth_db")
config.set_main_option("sqlalchemy.url", DB_URL)


def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo 'offline' (sin conexión real, solo genera SQL)."""
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
    """Función helper para ejecutar migraciones síncronas dentro del loop asíncrono."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Ejecuta migraciones en modo 'online' usando el engine asíncrono."""
    
    # Creamos el engine usando la configuración inyectada
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Ejecutamos la parte síncrona de Alembic dentro del contexto asíncrono
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Punto de entrada asíncrono
    asyncio.run(run_migrations_online())