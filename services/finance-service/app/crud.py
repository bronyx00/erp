import httpx
import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, Session
from sqlalchemy import func, String, extract, desc, and_, cast, or_
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from . import models, schemas, main
from jose import jwt
from .security import SECRET_KEY, ALGORITHM
from .models import FinanceSettings, Invoice

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
        
async def get_sales_total_by_employee(db: AsyncSession, tenant_id: int, employee_id: int, start_date: date, end_date: date) -> Decimal:
    """
    Suma el subtotal_usd de las facturas valiudas de un vendedor.
    """
    stmt = select(func.sum(models.Invoice.subtotal_usd)).where(
        and_(
            models.Invoice.tenant_id == tenant_id,
            models.Invoice.salesperson_id == employee_id,
            # Solo facturas pagadas cuentan para la comisión
            models.Invoice.status.in_(["PAID"]),
            # Filtramos por fecha de creación
            func.date(models.Invoice.created_at) >= start_date,
            func.date(models.Invoice.created_at) <= end_date
        )
    )
    
    result = await db.execute(stmt)
    total = result.scalar()
    
    return total if total is not None else Decimal(0)
        
async def get_customer_by_tax_id(tax_id: str, token: str):
    search_id = str(tax_id).strip().upper()
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CRM_URL}/customers?limit=1000", headers={"Authorization": f"Bearer {token}"})
            
            if resp.status_code == 200:
                body = resp.json()
                
                # --- CORRECCIÓN FINAL ---
                # Detectar si viene como 'data' (tu formato actual) o 'items' (formato estándar) o lista
                if isinstance(body, list):
                    customers = body
                elif isinstance(body, dict):
                    # Aquí estaba el error: buscabas "items", pero es "data"
                    customers = body.get("data", body.get("items", []))
                else:
                    customers = []
                # ------------------------

                for c in customers:
                    c_tax = c.get('tax_id')
                    if c_tax and str(c_tax).strip().upper() == search_id:
                        return c
                        
            return None
        except Exception as e:
            print(f"Error CRM Lookup: {e}")
            return None
        
async def get_next_invoice_number(db: AsyncSession, tenant_id: int) -> int:
    """Calcula el siguiente número correlativo para la empresa"""
    query = select(func.max(models.Invoice.invoice_number)).filter(models.Invoice.tenant_id == tenant_id)
    result = await db.execute(query)
    max_num = result.scalar()
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

async def get_finance_settings(db: AsyncSession, tenant_id: int):
    """
    OBtiene la configuración del tenant.
    Si no existe, crea una configuración por defecto.
    """
    # Intenta buscar la configuración existente
    stmt = select(FinanceSettings).where(FinanceSettings.tenant_id == tenant_id)
    result = await db.execute(stmt)
    settings = result.scalars().first()
    
    # Si no existe, creamos los valos por defecto
    if not settings:
        settings = FinanceSettings(
            tenant_id=tenant_id,
            enable_salesperson_selection=False,
            default_currency="USD"
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        
    return settings

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
        salesperson_id=invoice.salesperson_id,
        
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
            "items": [{"product_id": i.product_id, "quantity": i.quantity} for i in final_invoice.items],
            "origin": "inmediate"
        }
        main.publish_event("invoice.paid", paid_event)
    
    return final_invoice

async def get_quotes(
    db: AsyncSession,
    tenant_id: int,
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None
):
    offset = (page - 1) * limit
    
    conditions = [models.Quote.tenant_id == tenant_id]
    
    if search:
        search_term = f"%{search}%"
        conditions.append(
            or_(
                models.Quote.customer_name.ilike(search_term),
                models.Quote.customer_rif.ilike(search_term),
                cast(models.Quote.quote_number, String).ilike(search_term),
                models.Quote.created_by_email.ilike(search_term)
            )
        )
    
    # Contar Rapido
    count_query = select(func.count(models.Quote)).filter(*conditions)
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0
    
    # Consulta de Datos
    query = (
        select(models.Quote)
        .filter(*conditions)
        .order_by(models.Quote.id.desc())
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    data = result.scalars().all()
    
    return {
        "data": data,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if limit > 0 else 0
        }
    }    
    

async def get_invoices(
    db: AsyncSession, 
    tenant_id: int,
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None
):
    offset = (page - 1) * limit
    conditions = [models.Invoice.tenant_id == tenant_id]
    
    # Filtros Dinámicos
    if status:
        conditions.append(models.Invoice.status == status)
        
    if search:
        search_term = f"%{search}%"
        conditions.append(
            or_(
                models.Invoice.customer_name.ilike(search_term),
                models.Invoice.customer_rif.ilike(search_term),
                cast(models.Invoice.invoice_number, String).ilike(search_term),
                models.Invoice.control_number.ilike(search_term)
            )
        )
    
    # Contar Rapido
    count_query = select(func.count(models.Invoice.id)).filter(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Ordenar y Paginar
    query = (
        select(models.Invoice)
        .filter(*conditions)
        .order_by(models.Invoice.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    data = result.scalars().all()
    
    # Cálculo total de páginas
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

# --- GESTION DE COTIZACIONES ---
async def get_next_quote_number(db: AsyncSession, tenant_id: int) -> str:
    """Genera correlativo tipo COT-0001"""
    query = select(models.Quote.id).filter(models.Quote.tenant_id == tenant_id).order_by(desc(models.Quote.id)).limit(1)
    result = await db.execute(query)
    last_id = result.scalar() or 0
    return f"COT-{last_id + 1:05d}"

async def create_quote(db: AsyncSession, quote_in: schemas.QuoteCreate, tenant_id: int, token: str):
    # Datos Usuario y Tenant
    user_email, _ = get_user_from_token(token)
    tenant_data = await get_tenant_data(token)
    
    # Datos Cliente
    customer = await get_customer_by_tax_id(quote_in.customer_tax_id, token)
    if not customer:
        # Fallback si no existe.( Cambiar a la creacion )
        customer = {"name": "Cliente Nuevo", "rif": quote_in.customer_tax_id, "email": "", "address": "", "phone": ""}
        
    # Procesar Items (Precios y Totales)
    import asyncio
    product_tasks = [get_product_details(item.product_id, token) for item in quote_in.items]
    products_results = await asyncio.gather(*product_tasks)
    product_map = {p['id']: p for p in products_results if p}
    
    db_items = []
    total_base = Decimal(0)
    tax_rate = Decimal(tenant_data.get('tax_rate', 16)) // 100 if tenant_data.get('tax_active') else Decimal(0)
    
    for item in quote_in.items:
        product = product_map.get(item.product_id)
        if not product: continue
        
        if item.unit_price is not None and item.unit_price > 0:
            # Si viene Null o 0, usa el precio del sistema.
            # Si viene un número > 0, respeta el precio manual del vendedor.
            price = item.unit_price
        else:
            price = Decimal(product['price'])
        
        
        line_total = price * item.quantity
        
        total_base += line_total
        
        db_items.append(models.QuoteItem(
            product_id=product['id'],
            product_name=product['name'],
            description=item.description or product.get('description'),
            quantity=item.quantity,
            unit_price=price,
            total_price=line_total
        ))
        
    total_tax = round_money(total_base * tax_rate)
    total_final = round_money(total_base + total_tax)
    
    # Crear Cotización
    next_num = await get_next_quote_number(db, tenant_id)
    
    db_quote = models.Quote(
        tenant_id=tenant_id,
        quote_number=next_num,
        status="SENT",
        
        customer_id=customer.get('id'),
        customer_name=customer.get('name'),
        customer_rif=customer.get('tax_id') or quote_in.customer_tax_id,
        customer_email=customer.get('email'),
        customer_address=customer.get('address'),
        customer_phone=customer.get('phone'),
        
        date_issued=datetime.utcnow().date(),
        date_expires=quote_in.date_expires,
        
        currency=quote_in.currency,
        subtotal=total_base,
        tax_amount=total_tax,
        total=total_final,
        
        notes=quote_in.notes,
        terms=quote_in.terms,
        created_by_email=user_email,
        items=db_items
    )
    
    db.add(db_quote)
    await db.commit()
    
    query = (
        select(models.Quote)
        .options(selectinload(models.Quote.items))
        .filter(models.Quote.id == db_quote.id)
    )
    result = await db.execute(query)
    final_quote = result.scalars().first()
    
    return final_quote

async def convert_quote_to_invoice(db: AsyncSession, quote_in: int, tenant_id: int, token: str):
    """Convierte una Cotización en Factura Real"""
    # Buscar Cotización
    query = select(models.Quote).filter(models.Quote.id == quote_in, models.Quote.tenant_id == tenant_id).options(selectinload(models.Quote.items))
    result = await db.execute(query)
    quote = result.scalars().first()
    
    if not quote:
        raise ValueError("Cotización no encontrado")
    
    if quote.status == "INVOICED":
        raise ValueError("Esta cotización ya fue facturada")
    
    # Prepara objeto basado en la Cotización
    invoice_items = [
        schemas.InvoiceItemCreate(product_id=i.product_id, quantity=i.quantity)
        for i in quote.items
    ]
    
    invoice_in = schemas.InvoiceCreate(
        customer_tax_id=quote.customer_rif,
        currency=quote.currency,
        items=invoice_items,
        payment=None
    )
    
    # Crear Factura
    new_invoice = await create_invoice(db, invoice_in, tenant_id, token)
    
    # Actualizar estado de Cotización
    quote.status = "INVOICED"
    db.add(quote)
    await db.commit()
    
    return new_invoice


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