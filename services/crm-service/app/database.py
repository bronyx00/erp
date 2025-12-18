import os
from erp_common.database import DatabaseManager, Base

# Estandarizamos a DATABASE_URL para coincidir con el docker-compose
DATABASE_URL = os.getenv("DATABASE_URL")

# Inicialización del Manager común
db_manager = DatabaseManager(DATABASE_URL)

# Exportamos las herramientas para el resto de la app
engine = db_manager.engine
get_db = db_manager.get_db
Base = Base
AsyncSessionLocal = db_manager.session_factory