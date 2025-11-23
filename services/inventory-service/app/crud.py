from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas

async def get_products(db: AsyncSession, tenant_id: int):
    # Select * from products where is_active = true && tenant_id == tenant_id
    query = select(models.Product).filter(
        models.Product.tenant_id == tenant_id,
        models.Product.is_active == True
    )
    result = await db.execute(query)
    return result.scalars().all()

async def get_product_by_id(db: AsyncSession, product_id: int, tenant_id: int):
    # Dame el producto X solo si pertenece a mi EMPRESA
    query = select(models.Product).filter(
        models.Product.id == product_id,
        models.Product.tenant_id == tenant_id
    )
    result = await db.execute(query)
    return result.scalars().first()

async def create_product(db: AsyncSession, product: schemas.ProductCreate, tenant_id: int):
    db_product = models.Product(
        **product.model_dump(),
        tenant_id=tenant_id
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product