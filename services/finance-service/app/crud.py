import httpx
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from . import models, schemas

logger = logging.getLogger(__name__)

# URL internal de Docker
INVENTORY_SERVICE_URL = "http://inventory-service:8000"

async def get_product_details(product_id: int):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{INVENTORY_SERVICE_URL}/products/{product_id}")
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"Producto {product_id} no enocntrado en inventary-service")
            return None
        except Exception as e:
            logger.error(f"Error contactando inventory-service: {e}")
            return None

async def get_latest_rate(db: AsyncSession, currency_from: str = "USD", currency_to: str = "VES"):
    """Busca la tasa más reciente guardada por el Scheduler"""
    query = (
        select(models.ExchangeRate)
        .filter(
            models.ExchangeRate.currency_from == currency_from,
            models.ExchangeRate.currency_to == currency_to
        )
        .order_by(models.ExchangeRate.acquired_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalars().first()

async def create_invoice(db: AsyncSession, invoice: schemas.InvoiceCreate, owner_email: str):
    logger.info(f"Calculando factura para {invoice.customer_email} con {len(invoice.items)} items")
    # Calcular totales y validar productos
    total_amount = 0
    db_items = []
    
    for item in invoice.items:
        product = await get_product_details(item.product_id)
        if not product:
            raise ValueError(f"Producto ID {item.product_id} no encontrado")
        
        unit_price = float(product['price'])
        line_total = unit_price * item.quantity
        total_amount += line_total
        
        db_items.append(models.InvoiceItem(
            product_id=item.product_id,
            product_name=product['name'],
            quantity=item.quantity,
            unit_price=unit_price,
            total_price=line_total
        ))
    
    # Crear Factura
    db_invoice = models.Invoice(
        owner_email=owner_email,
        customer_email=invoice.customer_email,
        amount=total_amount,
        currency=invoice.currency,
        status="ISSUED",
        items=db_items
    )
    
    # Buscar Tasa de Cambio
    if invoice.currency == "USD":
        rate_entry = await get_latest_rate(db)
        if rate_entry:
            # Calculamos el contravalor
            db_invoice.exchange_rate = rate_entry.rate
            db_invoice.amount_ves = float(total_amount) * float(rate_entry.rate)
        else:
            logger.warning("⚠️ ADVERTENCIA: No se encontró tasa de cambio en la DB. Guardando sin conversión.")
    
    # Guardar
    db.add(db_invoice)
    await db.commit()
    await db.refresh(db_invoice)
    
    query = (
        select(models.Invoice)
        .options(selectinload(models.Invoice.items))
        .filter(models.Invoice.id == db_invoice.id)
    )
    result = await db.execute(query)
    invoice_loaded = result.scalars().first()
    
    return invoice_loaded

async def get_invoices(db: AsyncSession, owner_email: str):
    query = (
        select(models.Invoice)
        .filter(models.Invoice.owner_email == owner_email)
        .options(selectinload(models.Invoice.items))
        )
    result = await db.execute(query)
    return result.scalars().all()