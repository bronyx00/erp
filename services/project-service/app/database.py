import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# URL de conexión (La leeremos de las variables de entorno de Docker)
DATABASE_URL = os.getenv("PROJECT_DATABASE_URL", "postgresql+asyncpg://admin:admin@project_db:5432/project_db")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# Dependencia para obtener la DB en cada petición
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()