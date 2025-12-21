import os
from erp_common.database import DatabaseManager, Base

DATABASE_URL = os.getenv("DATABASE_URL")

db_manager = DatabaseManager(DATABASE_URL)

engine = db_manager.engine
get_db = db_manager.get_db
Base = Base
AsyncSessionLocal = db_manager.session_factory