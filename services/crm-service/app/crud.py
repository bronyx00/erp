from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas

async def get_customers(db: AsyncSession, tenant_id: int):
    # Solo devuelve los clientes de esta EMPRESAkhr
    query = select(models.Customer).filter(
        models.Customer.tenant_id == tenant_id,
        models.Customer.is_active == True
    )
    result = await db.execute(query)
    return result.scalars().all()

async def create_customer(db: AsyncSession, customer: schemas.CustomerCreate, tenant_id: int):
    db_customer = models.Customer(
        **customer.model_dump(),
        tenant_id=tenant_id # Asigna el dueño automáticamente
    )
    db.add(db_customer)
    await db.commit()
    await db.refresh(db_customer)
    return db_customer