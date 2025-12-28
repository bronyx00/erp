from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from typing import Optional, Dict, Any
from . import models, schemas

async def get_product_by_sku(db: AsyncSession, sku: str, tenant_id: int):
    """Busca un producto por SKU para validaciones."""
    query = select(models.Product).filter(
        models.Product.sku == sku,
        models.Product.tenant_id == tenant_id
    )
    result = await db.execute(query)
    return result.scalars().first()

async def get_products(
    db: AsyncSession, 
    tenant_id: int, 
    page: int = 1, 
    limit: int = 50,
    search: Optional[str] = None,
    category: Optional[str] = None
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
    
    if category and category != 'Todas':
        conditions.append(models.Product.category == category)
        
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
    db_product = models.Product(
        **product.model_dump(),
        tenant_id=tenant_id
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

async def update_product(db: AsyncSession, product_id: int, updates: schemas.ProductUpdate, tenant_id: int):
    db_product = await get_product_by_id(db, product_id, tenant_id)
    if not db_product:
        return None
        
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
        
    await db.commit()
    await db.refresh(db_product)
    return db_product

async def get_categories_summary(db: AsyncSession, tenant_id: int):
    """
    Retorna las categorías únicas y el conteo de productos activos en cada una.
    """
    query = (
        select(models.Product.category, func.count(models.Product.id))
        .filter(models.Product.tenant_id == tenant_id, models.Product.is_active == True)
        .group_by(models.Product.category)
        .order_by(models.Product.category.asc())
    )
    result = await db.execute(query)
    # [{"name": "Bebidas", "count": 15}, ...]
    return [{"name": row[0], "count": row[1]} for row in result.all()]

async def delete_product(db: AsyncSession, product_id: int, tenant_id: int):
    """
    Realiza un borrado lógico (Soft Delete) del producto.
    No elimina la fila de la BD, solo marca is_active = False.
    """
    # Reutilizamos la función de búsqueda que ya tienes
    product = await get_product_by_id(db, product_id, tenant_id)
    
    if product:
        product.is_active = False
        await db.commit()
        await db.refresh(product)
        
    return product