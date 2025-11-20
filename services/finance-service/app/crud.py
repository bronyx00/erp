from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas

async def create_invoice(db: AsyncSession, invoice: schemas.InvoiceCreate):
    db_invoice = models.Invoice(
        customer_email=invoice.customer_email,
        amount=invoice.amount,
        currency=invoice.currency,
        status="ISSUED" # Emitida
    )
    db.add(db_invoice)
    await db.commit()
    await db.refresh(db_invoice)
    return db_invoice

async def get_invoices(db: AsyncSession):
    result = await db.execute(select(models.Invoice))
    return result.scalars().all()