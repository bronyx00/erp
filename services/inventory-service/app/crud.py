from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from . import models, schemas

async def get_products(db: AsyncSession, tenant_id: int, page: int = 1, limit: int = 50):
    offset = (page - 1) * limit
    
    # Select * from products where is_active = true && tenant_id == tenant_id
    query = select(models.Product).filter(
        models.Product.tenant_id == tenant_id,
        models.Product.is_active == True
    )
    
    # Contar Total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Obtiene Datos Paginados
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    data = result.scalars().all()
    
    # Calcular Páginas
    total_pages = (total + limit - 1) // limit
    
    return {
        "data": data,
        "meta": {
            "total": total,
            "page": page, 
            "limit": limit,
            "total_pages": total_pages
        }
    }

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