import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Base declarativa común para todos los modelos
Base = declarative_base()

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        # Detectar si estamos en modo debug 
        self.debug = os.getenv("ENV_MODE", "dev") == "dev"
        
        self.engine = create_async_engine(
            self.database_url,
            echo=self.debug,
            future=True
        )
        self.session_factory = sessionmaker(
            self.engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )

    async def get_db(self):
        async with self.session_factory() as session:
            try:
                yield session
            finally:
                await session.close()