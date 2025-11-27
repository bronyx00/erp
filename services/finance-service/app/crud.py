import httpx
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from datetime import datetime
from decimal import Decimal
from . import models, schemas

logger = logging.getLogger(__name__)

# URL internal de Docker
INVENTORY_SERVICE_URL = "http://inventory-service:8000"

async def get_product_details(product_id: int, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{INVENTORY_SERVICE_URL}/products/{product_id}", headers=headers)
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"Producto {product_id} error: {resp.status_code} - {resp.text}")
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

async def get_next_invoice_number(db: AsyncSession, tenant_id: int) -> int:
    """Busca el último número de factura de esta empresa y suma 1"""
    query = select(func.max(models.Invoice.invoice_number)).filter(models.Invoice.tenant_id == tenant_id)
    result = await db.execute(query)
    max_enum = result.scalar()
    return (max_enum or 0) + 1

async def create_invoice(db: AsyncSession, invoice: schemas.InvoiceCreate, tenant_id: int, token: str, tenant_data: dict):
    
    # Obtener consecutivo
    next_number = await get_next_invoice_number(db, tenant_id)
    
    # Cálculos (Subtotales e IVA)
    total_base = 0
    total_tax = 0
    db_items = []
    
    for item in invoice.items:
        product = await get_product_details(item.product_id, token)
        if not product:
            raise ValueError(f"Producto ID {item.product_id} no encontrado o sin permiso")
        
        unit_price = Decimal(product['price'])
        
        # Lógica de Impuesto según configuración
        item_subtotal = unit_price * item.quantity
        item_tax = 0
        
        if tenant_data.get('tax_active', True):
            rate = Decimal(tenant_data.get('tax_rate', 16)) / 100
            item_tax = item_subtotal * rate
            
        total_base += item_subtotal
        total_tax += item_tax
        
        db_items.append(models.InvoiceItem(
            product_id=item.product_id,
            product_name=product['name'],
            quantity=item.quantity,
            unit_price=unit_price,
            total_price=item_subtotal
        ))
    
    total_final = total_base + total_tax
    
    # Crear Factura con Datos Fiscales
    db_invoice = models.Invoice(
        tenant_id=tenant_id,
        invoice_number=next_number,
        control_number=f"00-{next_number}",
        
        # Snapshot de la empresa
        company_name_snapshot=tenant_data.get('business_name'),
        company_rif_snapshot=tenant_data.get('rif'),
        company_address_snapshot=tenant_data.get('address'),
        
        # Cliente
        customer_email=invoice.customer_email,
        # Buscar luego los datos del cliente por CRM
        
        amount=total_final,
    )
    
    # Buscar Tasa de Cambio
    if invoice.currency == "USD":
        rate_entry = await get_latest_rate(db)
        if rate_entry:
            # Calculamos el contravalor
            db_invoice.exchange_rate = rate_entry.rate
            db_invoice.amount_ves = float(total_final) * float(rate_entry.rate)
        else:
            logger.warning("⚠️ ADVERTENCIA: No se encontró tasa de cambio en la DB. Guardando sin conversión.")
    
    # Guardar
    db.add(db_invoice)
    await db.commit()
    await db.refresh(db_invoice)
    
    query = (
        select(models.Invoice)
        .options(
            selectinload(models.Invoice.items),
            selectinload(models.Invoice.payments)
        )
        .filter(models.Invoice.id == db_invoice.id)
    )
    result = await db.execute(query)
    
    return result.scalars().first()

async def get_invoices(db: AsyncSession, tenant_id: int):
    query = (
        select(models.Invoice)
        .filter(models.Invoice.tenant_id == tenant_id)
        .options(selectinload(models.Invoice.items), selectinload(models.Invoice.payments))
        .order_by(models.Invoice.created_at.desc())
        )
    result = await db.execute(query)
    return result.scalars().all()

async def create_payment(db: AsyncSession, payment: schemas.PaymentCreate, tenant_id: int):
    # Buscar la factura y verificar que pertenezca al usuario
    query = (
        select(models.Invoice)
        .filter(models.Invoice.id == payment.invoice_id, models.Invoice.tenant_id == tenant_id)
        .options(
            selectinload(models.Invoice.payments),
            selectinload(models.Invoice.items)
        )
    )
    result = await db.execute(query)
    invoice = result.scalars().first()
    
    if not invoice:
        raise ValueError("Factura no encontrada o acceso denegado")
    
    # Calcular saldo
    total_paid = sum(p.amount for p in invoice.payments)
    balance_due = invoice.amount - total_paid
    
    if payment.amount > balance_due:
        # Se puede cambiar cuando queramos hacer el estado de 'crédito a favor', por ahora solo emite error
        raise ValueError(f"El monto excede la deuda. Saldo pendiente: {balance_due}")
    
    # Crear Pago
    db_payment = models.Payment(
        invoice_id=payment.invoice_id,
        amount=payment.amount,
        currency=invoice.currency,
        payment_method=payment.payment_method,
        reference=payment.reference,
        notes=payment.notes
    )
    db.add(db_payment)
    
    # Actualizar Status de la Factura
    new_total_paid = total_paid + payment.amount
    is_fully_paid = False # Bandera para saber si debemos emitir evento
    
    if new_total_paid >= invoice.amount:
        invoice.status = "PAID"
        is_fully_paid = True
    else:
        invoice.status = "PARTIALLY_PAID"
        
    db.add(invoice) # Actualiza la factura también
    
    await db.commit()
    await db.refresh(db_payment)
    return db_payment, invoice, is_fully_paid

async def get_invoice_by_id(db: AsyncSession, invoice_id: int, tenant_id: int):
    """Busca una factura asegurando que pertenece al Tenant."""
    query = (
        select(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.tenant_id == tenant_id)
        .options(selectinload(models.Invoice.items), selectinload(models.Invoice.payments))
    )
    result = await db.execute(query)
    return result.scalars().first()

async def set_invoice_void(db: AsyncSession, invoice: models.Invoice):
    """Marca la factura como anulada y guarda en DB."""
    invoice.status = "VOID"
    db.add(invoice)
    await db.commit()
    
    # Recargamos para devolver el objeto actualizado y limpio
    await db.refresh(invoice)
    return invoice

# --- REPORTES ---
async def get_dashboard_metrics(db: AsyncSession, tenant_id: int):
    today = datetime.utcnow().date()
    start_of_month = today.replace(day=1)
    
    # Ventas de Hoy
    query_today = select(
        func.sum(models.Invoice.amount),
        func.count(models.Invoice.id)
    ).filter(
        models.Invoice.tenant_id == tenant_id,
        models.Invoice.status != "VOID", # Ignorar anuladas
        func.date(models.Invoice.created_at) == today
    )
    result_today = await db.execute(query_today)
    today_amount, today_count = result_today.first()
    
    # Ventas del Mes
    query_month = select(func.sum(models.Invoice.amount)).filter(
        models.Invoice.tenant_id == tenant_id,
        models.Invoice.status != "VOID",
        models.Invoice.created_at >= start_of_month
    )
    result_month = await db.execute(query_month)
    month_amount = result_month.scalar()
    
    # Por Cobrar (Facturas ISSUED o PARTIALLY_PAID)
    # Nota: es aproximado. Sumaremos el total de facturas no pagadas completamente
    query_pending = select(func.sum(models.Invoice.amount)).filter(
        models.Invoice.tenant_id == tenant_id,
        models.Invoice.status.in_(["ISSUED", "PARTIALLY_PAID"])
    )
    result_pending = await db.execute(query_pending)
    pending_amount = result_pending.scalar()
    
    return {
        "today_sales": today_amount or 0,
        "total_invoices_today": today_count or 0,
        "month_sales": month_amount or 0,
        "pending_balance": pending_amount or 0
    }