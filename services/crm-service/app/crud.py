from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas

async def get_customers(db: AsyncSession, owner_email: str):
    # Solo devuelve los clientes de este usuario
    query = select(models.Customer).filter(
        models.Customer.owner_email == owner_email,
        models.Customer.is_active == True
    )
    result = await db.execute(query)
    return result.scalars().all()

async def create_customer(db: AsyncSession, customer: schemas.CustomerCreate, owner_email: str):
    db_customer = models.Customer(
        **customer.model_dump(),
        owner_email=owner_email # Asigna el dueño automáticamente
    )
    db.add(db_customer)
    await db.commit()
    await db.refresh(db_customer)
    return db_customer