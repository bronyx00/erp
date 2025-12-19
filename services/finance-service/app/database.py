import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from erp_common.database import DatabaseManager, Base

# 1. Estandarización: Usamos la misma variable que en el docker-compose
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Inicialización Asíncrona (Para FastAPI)
db_manager = DatabaseManager(DATABASE_URL)
engine = db_manager.engine
get_db = db_manager.get_db
Base = Base
AsyncSessionLocal = db_manager.session_factory

# 3. Inicialización Síncrona (NECESARIA para APScheduler/Background Tasks)
# El scheduler corre en hilos normales, no soporta async/await nativo fácilmente.
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "") # Hack para quitar el driver async
sync_engine = create_engine(SYNC_DATABASE_URL, echo=db_manager.debug)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)