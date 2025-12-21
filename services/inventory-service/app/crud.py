from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from typing import Optional, Dict, Any
from . import models, schemas

async def get_products(
    db: AsyncSession, 
    tenant_id: int, 
    page: int = 1, 
    limit: int = 50,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Lista productos con paginación.
    Permite buscar por Nombre O por SKU.
    """
    
    offset = (page - 1) * limit
    
    # Condiciones base
    conditions = [
        models.Product.tenant_id == tenant_id,
        models.Product.is_active == True
    ]
    
    # Filtro de búsqueda si existe
    if search:
        term = f"%{search}%"
        conditions.append(
            or_(
                models.Product.name.ilike(term),
                models.Product.sku.ilike(term)
            )
        )
        
    # 1. Conteo optimizado
    count_query = select(func.count(models.Product.id)).filter(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 2. Obtener Datos
    query = (
        select(models.Product)
        .filter(*conditions)
        .order_by(models.Product.name.asc())
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
    """Busca un producto por ID dentro de la empresa."""
    query = select(models.Product).filter(
        models.Product.id == product_id,
        models.Product.tenant_id == tenant_id
    )
    result = await db.execute(query)
    return result.scalars().first()

async def create_product(db: AsyncSession, product: schemas.ProductCreate, tenant_id: int):
    """Busca un producto por SKU para validaciones."""
    db_product = models.Product(
        **product.model_dump(),
        tenant_id=tenant_id
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product