from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas

async def get_products(db: AsyncSession):
    # Select * from products where is_active = true
    result = await db.execute(select(models.Product).where(models.Product.is_active == True))
    return result.scalars().all()

async def get_product_by_id(db: AsyncSession, product_id: int):
    result = await db.execute(select(models.Product).filter(models.Product.id == product_id))
    return result.scalars().first()

async def create_product(db: AsyncSession, product: schemas.ProductCreate):
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product