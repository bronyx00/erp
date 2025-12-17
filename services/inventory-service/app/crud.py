from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import Optional
from . import models, schemas

async def get_products(
    db: AsyncSession, 
    tenant_id: int, 
    page: int = 1, 
    limit: int = 50,
    search: Optional[str] = None
):
    
    offset = (page - 1) * limit
    
    # Define condiciones base para reusarlas en conteo y búsqueda
    conditions = [
        models.Product.tenant_id == tenant_id,
        models.Product.is_active == True
    ]
    
    # Filtro de búsqueda si existe
    if search:
        conditions.append(models.Product.name.ilike(f"%{search}%"))
        
    # Conteo optimizado
    count_query = select(func.count(models.Product.id)).filter(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Obtener Datos
    query = (
        select(models.Product)
        .filter(*conditions)
        .order_by(models.Product.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    data = result.scalars().all()
    
    # Calcular Páginas
    total_pages = (total + limit - 1) // limit if limit > 0 else 0

    
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