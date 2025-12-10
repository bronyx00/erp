import httpx
import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, Session
from sqlalchemy import func, String, extract
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from . import models, schemas, main
from jose import jwt
from .security import SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)

# URL internal de Docker
INVENTORY_SERVICE_URL = "http://inventory-service:8000"
AUTH_URL = "http://auth-service:8000"
CRM_URL = "http://crm-service:8000"

# Función auxiliar para redondear dinero
def round_money(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"))

# Helper para decodificar usuario
def get_user_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, ALGORITHM)
        return payload.get("sub"), payload.get("role")
    except Exception as e:
        logger.error(f"Error decodificando token: {e}")
        return None, None

# ---- HELPERS PARA DATOS EXTERNOS ----
async def get_product_details(product_id: int, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{INVENTORY_SERVICE_URL}/products/{product_id}", headers=headers)
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            logger.error(f"Error Inventory: {e}")
            return None

async def get_tenant_data(token: str):
    """Obtiene los datos fiscales de la empresa desde Auth"""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{AUTH_URL}/tenant/me", headers={"Authorization": f"Bearer {token}"})
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            logger.error(f"Error Auth: {e}")
            return None
        
async def get_customer_by_tax_id(tax_id: str, token: str):
    """Busca datos del cliente en CRM usando el tax_id"""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CRM_URL}/customers", headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                customers = resp.json()
                for c in customers:
                    if c.get('tax_id') == tax_id:
                        return c
            return None
        except Exception as e:
            logger.error(f"Error CRM: {e}")
            return None
        
async def get_next_invoice_number(db: AsyncSession, tenant_id: int) -> int:
    """Calcula el siguiente número correlativo para la empresa"""
    query = select(func.max(models.Invoice.invoice_number)).filter(models.Invoice.tenant_id == tenant_id)
    result = await db.execute(query)
    max_num = result.scalr()
    return (max_num or 0) + 1

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

async def create_invoice(db: AsyncSession, invoice: schemas.InvoiceCreate, tenant_id: int, token: str):
    """
    Crea una factura y opcionalmente procesa su pago inmediato.
    Optimizado para consultar productos en paralelo.
    """
    # Obtiene datos del usuario
    user_email, user_role = get_user_from_token(token)
    
    # Obtiene Datos Fiscales de la Empresa
    tenant_data = await get_tenant_data(token)
    
    if not tenant_data:
        raise ValueError("No se pudieron obtener los datos fiscales de la empresa")
    
    # Obtener Datos del Cliente
    customer_data = {}
    if invoice.customer_tax_id:
        customer_data = await get_customer_by_tax_id(invoice.customer_tax_id, token) or {}
        
    product_tasks = [get_product_details(item.product_id, token) for item in invoice.items]
    products_results = await asyncio.gather(*product_tasks)
    
    # Mapa para acceso rápido
    products_map = {
        p['id']: p for p in products_results if p is not None
    }

    # Cálculos (Subtotales e IVA)
    total_base = Decimal(0)
    total_tax = Decimal(0)
    db_items = []
    
    tax_rate = Decimal(tenant_data.get('tax_rate', 16)) / 100 if tenant_data.get('tax_active') else Decimal(0)
        
    for item in invoice.items:
        # Recupera del mapa en memoria
        product = products_map.get(item.product_id)
        
        if not product:
            raise ValueError(f"Producto ID {item.product_id} no encontrado")
        
        # Validar Stock
        if product['stock'] < item.quantity:
            raise ValueError(f"Stock insuficiente para {product['name']}")
        
        unit_price = Decimal(product['price'])
        
        # Lógica de Impuesto según configuración
        item_subtotal = unit_price * item.quantity
        
        # Cálculo de impuesto por ítem
        item_tax = round_money(item_subtotal * tax_rate)
            
        total_base += item_subtotal
        total_tax += item_tax
        
        db_items.append(models.InvoiceItem(
            product_id=item.product_id,
            product_name=product['name'],
            quantity=item.quantity,
            unit_price=unit_price,
            total_price=item_subtotal
        ))
    
    total_final = round_money(total_base + total_tax)
    
    # Determinar Estado y Pagos
    # Si viene un pago dede el POS que cubre el total, la factura nace PAGADA
    initial_status = "ISSUED"
    db_payments = []
    
    if invoice.payment:
        # Valida que el monto sea suficiente
        if invoice.payment.amount >= total_final:
            initial_status = "PAID"
        elif invoice.payment.amount > 0:
            inicial_status = "PARTIALLY_PAID"
            
        # Crea el objeto de pago en memoria para guardalo junto con la factura
        payment_entry = models.Payment(
            amount=invoice.payment.amount,
            currency=invoice.currency,
            payment_method=invoice.payment.payment_method,
            reference=invoice.payment.reference,
            notes=invoice.payment.notes
        )
        
        db_payments.append(payment_entry)
    
    # Obtener Consecutivo Fiscal
    next_number = await get_next_invoice_number(db, tenant_id)
    
    # Tasa de Cambio
    rate_val = Decimal(1)
    if invoice.currency == "USD":
        rate_entry = await get_latest_rate(db)
        if rate_entry:
            rate_val = rate_entry.rate
    
    # Crear Objeto Factura (Snapshot)
    db_invoice = models.Invoice(
        tenant_id=tenant_id,
        invoice_number=next_number,
        control_number=f"00-{next_number:08d}",
        
        # Snapshot Empresa
        company_name_snapshot=tenant_data.get('name'), # Nombre comercial
        company_rif_snapshot=tenant_data.get('rif'),
        company_address_snapshot=tenant_data.get('address'),
        
        # Snapshot Cliente
        customer_name=customer_data.get('name') or 'CLIENTE GENÉRICO',
        customer_rif=invoice.customer_tax_id,
        customer_email=customer_data.get('email') or f"cliente@email.com",
        customer_address=customer_data.get('address'),
        customer_phone=customer_data.get('phone'),
        
        # Montos Globales
        subtotal_usd=total_base,
        tax_amount_usd=total_tax,
        total_usd=total_final,
        
        currency=invoice.currency,
        exchange_rate=rate_val,
        amount_ves=total_final * rate_val,
        
        # Firmas
        created_by_email=user_email,
        created_by_role=user_role,
        
        status=initial_status,
        items=db_items,
        payments=db_payments
    )
    
    # Guardar
    db.add(db_invoice)
    await db.commit()
    
    query = (
        select(models.Invoice)
        .options(
            selectinload(models.Invoice.items),
            selectinload(models.Invoice.payments) 
        )
        .filter(models.Invoice.id == db_invoice.id)
    )
    result = await db.execute(query)
    final_invoice = result.scalars().first()
    
    event_data = {
        "id": final_invoice.id,
        "tenant_id": tenant_id,
        "total_amount": float(final_invoice.total_usd),
        "currency": final_invoice.currency,
        "status": final_invoice.status,
        "date": str(final_invoice.created_at)
    }
    
    main.publish_event("invoice.created", event_data)
    
    if initial_status == "PAID":
        paid_event = {
            "invoice_id": final_invoice.id,
            "tenant_id": tenant_id,
            "total_amount": float(final_invoice.total_usd),
            "paid_at": str(datetime.utcnow()),
            "items": [{"product_id": i.product_id, "quantity": i.quantity} for i in final_invoice.items]
        }
        main.publish_event("invoice.paid", paid_event)
    
    return final_invoice


async def get_invoices(
    db: AsyncSession, 
    tenant_id: int,
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None
):
    offset = (page - 1) * limit
    
    # Query Base
    query = select(models.Invoice).filter(models.Invoice.tenant_id == tenant_id)
    
    # Filtros Dinámicos
    if status:
        query = query.filter(models.Invoice.status == status)
        
    if search:
        # Búsqueda insesible a mayúsculas en nombre o número
        search_term = f"%{search}%"
        query = query.filter(
            (models.Invoice.customer_name.ilike(search_term)) |
            (models.Invoice.invoice_number.cast(String).ilike(search_term))
        )
    
    # Contar total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Ordenar y Paginar
    query = query.order_by(models.Invoice.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    # Cálculo total de páginas
    total_pages = (total + limit - 1) // limit 
    
    return {
        "data": invoices,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    }

async def create_payment(db: AsyncSession, payment: schemas.PaymentCreate, tenant_id: int):
    # Buscar la factura y verificar que pertenezca al usuario
    query = (
        select(models.Invoice)
        .filter(models.Invoice.id == payment.invoice_id, models.Invoice.tenant_id == tenant_id)
        .options(
            selectinload(models.Invoice.payments),
            selectinload(models.Invoice.items)
        )
        .with_for_update()
    )
    
    result = await db.execute(query)
    invoice = result.scalars().first()
    
    if not invoice:
        raise ValueError("Factura no encontrada o acceso denegado")
    
    # Calcular saldo
    total_paid = sum(p.amount for p in invoice.payments)
    balance_due = invoice.total_usd - total_paid
    
    payment_amount_rounded = round_money(payment.amount)
    
    if payment_amount_rounded > balance_due + Decimal("0.01"):
        raise ValueError(f"El monto excede la deuda. Saldo pendiente: {balance_due}")
    
    # Crear Pago
    db_payment = models.Payment(
        invoice_id=payment.invoice_id,
        amount=payment_amount_rounded,
        currency=invoice.currency,
        payment_method=payment.payment_method,
        reference=payment.reference,
        notes=payment.notes
    )
    db.add(db_payment)
    
    # Actualizar Status de la Factura
    new_total_paid = total_paid + payment_amount_rounded
    is_fully_paid = False # Bandera para saber si debemos emitir evento
    
    if new_total_paid >= invoice.total_usd:
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
        func.sum(models.Invoice.total_usd)).filter(
        models.Invoice.tenant_id == tenant_id,
        models.Invoice.status != "VOID", # Ignorar anuladas
        func.date(models.Invoice.created_at) == today
    )
    result_today = await db.execute(query_today)
    today_sales = result_today.scalar() or 0
    
    # Conteo Facturas Hoy
    query_count = select(func.count(models.Invoice.id)).filter(
        models.Invoice.tenant_id == tenant_id,
        func.date(models.Invoice.created_at) == today
    )
    result_count = await db.execute(query_count)
    count_today = result_count.scalar() or 0
    
    # Ventas del Mes
    query_month = select(func.sum(models.Invoice.total_usd)).filter(
        models.Invoice.tenant_id == tenant_id,
        models.Invoice.status != "VOID",
        models.Invoice.created_at >= start_of_month
    )
    result_month = await db.execute(query_month)
    month_sales = result_month.scalar() or 0
    
    # Por Cobrar (Facturas ISSUED o PARTIALLY_PAID)
    # Nota: es aproximado. Sumaremos el total de facturas no pagadas completamente
    query_pending = select(func.sum(models.Invoice.total_usd)).filter(
        models.Invoice.tenant_id == tenant_id,
        models.Invoice.status.in_(["ISSUED", "PARTIALLY_PAID"])
    )
    result_pending = await db.execute(query_pending)
    pending_balance = result_pending.scalar() or 0
    
    return {
        "today_sales": today_sales,
        "total_invoices_today": count_today,
        "month_sales": month_sales,
        "pending_balance": pending_balance
    }

async def get_sales_report_by_method(db: AsyncSession, tenant_id: int):
    """
    Agrupa los pagos por Fecha, Método y Moneda.
    """
    query = (
        select(
            func.date(models.Payment.created_at).label("payment_date"),
            models.Payment.payment_method,
            models.Payment.currency,
            func.sum(models.Payment.amount).label("total_amount"),
            func.count(models.Payment.id).label("count")
        )
        .join(models.Invoice, models.Invoice.id == models.Payment.invoice_id)
        .filter(models.Invoice.tenant_id == tenant_id)
        .group_by(
            func.date(models.Payment.created_at),
            models.Payment.payment_method,
            models.Payment.currency
        )
        .order_by(func.date(models.Payment.created_at).desc())
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    report_data = []
    for row in rows:
        report_data.append({
            "date": row.payment_date,
            "payment_method": row.payment_method,
            "currency": row.currency,
            "total_amount": row.total_amount,
            "transaction_count": row.count
        })
        
    return report_data

async def get_sales_compatison(db: AsyncSession, tenant_id: int):
    today = date.today()
    current_year = today.year
    last_year = current_year - 1
    
    # Función auxiliar para consultar un año específico
    async def get_year_data(year_val):
        query = (
            select(
                extract('month', models.Invoice.created_at).label('month'),
                func.sum(models.Invoice.total_usd).label('total')
            )
            .filter(
                models.Invoice.tenant_id == tenant_id,
                models.Invoice.status != 'VOID',
                extract('year', models.Invoice.created_at) == year_val
            )
            .group_by('month')
            .order_by('month')
        )
        result = await db.execute(query)
        return {int(row.month): float(row.total) for row in result.all()}
    
    current_data = await get_year_data(current_year)
    last_year_data = await get_year_data(last_year)
    
    # Formatear respuesta cominada para Chart.js
    combined_data = []
    month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    
    for i in range (1, 13):
        combined_data.append({
            "month": month_names[i-1],
            "current_year": current_data.get(i, 0.0),
            "last_year": last_year_data.get(i, 0.0)
        })
        
    return combined_data