from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from . import models, schemas

async def get_customers(db: AsyncSession, tenant_id: int, page: int = 1, limit: int = 50):
    offset = (page - 1) * limit
    
    # Solo devuelve los clientes de esta EMPRESAkhr
    query = select(models.Customer).filter(
        models.Customer.tenant_id == tenant_id,
        models.Customer.is_active == True
    )
    
    # Contar
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0
    
    # Paginar
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    data = result.scalars().all()
    
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

async def create_customer(db: AsyncSession, customer: schemas.CustomerCreate, tenant_id: int):
    db_customer = models.Customer(
        **customer.model_dump(),
        tenant_id=tenant_id # Asigna el dueño automáticamente
    )
    db.add(db_customer)
    await db.commit()
    await db.refresh(db_customer)
    return db_customer