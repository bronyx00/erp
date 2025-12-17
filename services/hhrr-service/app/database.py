import os
from erp_common.database import DatabaseManager, Base

# URL de conexión 
DATABASE_URL = os.getenv("HHRR_DATABASE_URL")

# Inicialización de Manager común
db_manager = DatabaseManager(DATABASE_URL)

# Exporta las variables que la app espera
engine = db_manager.engine
get_db = db_manager.get_db
Base = Base
AsyncSessionLocal = db_manager.session_factory