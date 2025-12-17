from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from . import models, schemas

async def get_customers(db: AsyncSession, tenant_id: int, page: int = 1, limit: int = 50, search: Optional[str] = None):
    offset = (page - 1) * limit
    conditions = [models.Customer.tenant_id == tenant_id, models.Customer.is_active == True]
    
    if search:
        conditions.append(models.Customer.name.ilike(f"%{search}%"))

    # Conteo Rápido
    count_query = select(func.count(models.Customer.id)).filter(*conditions)
    total = (await db.execute(count_query)).scalar() or 0
    
    # Datos
    query = (
        select(models.Customer)
        .filter(*conditions)
        .order_by(models.Customer.name.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    
    return {
        "data": result.scalars().all(),
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if limit > 0 else 0
        }
    }

async def create_customer(db: AsyncSession, customer: schemas.CustomerCreate, tenant_id: int):
    db_customer = models.Customer(
        **customer.model_dump(),
        tenant_id=tenant_id # Asigna el dueño automáticamente
    )
    db.add(db_customer)
    await db.commit()
    await db.refresh(db_customer)
    return db_customer