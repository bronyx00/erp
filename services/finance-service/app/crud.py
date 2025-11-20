from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas

async def get_latest_rate(db: AsyncSession, currency_from: str = "USD", currenct_to: str = "VES"):
    """Busca la tasa más reciente guardada por el Scheduler"""
    query = (
        select(models.ExchangeRate)
        .filter(
            models.ExchangeRate.currency_from == currency_from,
            models.ExchangeRate.currency_to == currenct_to
        )
        .order_by(models.ExchangeRate.acquired_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalars().first()

async def create_invoice(db: AsyncSession, invoice: schemas.InvoiceCreate):
    # Preparar objeto factura
    db_invoice = models.Invoice(
        customer_email=invoice.customer_email,
        amount=invoice.amount,
        currency=invoice.currency,
        status="ISSUED" # Emitida
    )
    
    # Buscar Tasa de Cambio
    if invoice.currency == "USD":
        rate_entry = await get_latest_rate(db)
        if rate_entry:
            # Calculamos el contravalor
            db_invoice.exchange_rate = rate_entry.rate
            db_invoice.amount_ves = invoice.amount * rate_entry.rate
        else:
            print("⚠️ ADVERTENCIA: No se encontró tasa de cambio en la DB. Guardando sin conversión.")
    
    # Guardar
    db.add(db_invoice)
    await db.commit()
    await db.refresh(db_invoice)
    return db_invoice

async def get_invoices(db: AsyncSession):
    result = await db.execute(select(models.Invoice))
    return result.scalars().all()