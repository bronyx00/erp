import os
from erp_common.database import DatabaseManager, Base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# URL de conexión 
DATABASE_URL = os.getenv("FINANCE_DATABASE_URL")

# Inicialización de Manager común
db_manager = DatabaseManager(DATABASE_URL)

# Exporta las variables que la app espera
engine = db_manager.engine
get_db = db_manager.get_db
Base = Base
AsyncSessionLocal = db_manager.session_factory

# URL Síncrona (Para el Scheduler/Background Tasks)
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")
sync_engine = create_engine(SYNC_DATABASE_URL, echo=db_manager.debug)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)