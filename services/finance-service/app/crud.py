import httpx
import logging
import os
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, String, extract, desc, and_, cast, or_, extract
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from decimal import Decimal
from . import models, schemas
from .events import publish_event
from jose import jwt
from erp_common.security import SECRET_KEY, ALGORITHM
from .models import FinanceSettings

logger = logging.getLogger(__name__)

# URLs de otros microservicios (Leídas del ENV o defaults de Docker)
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventory-service:8000")
AUTH_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
CRM_URL = os.getenv("CRM_SERVICE_URL", "http://crm-service:8000")

# --- UTILIDADES ---
def round_money(amount: Decimal) -> Decimal:
    """Redondea un monto a 2 decimales."""
    return amount.quantize(Decimal("0.01"))

def get_user_from_token(token: str):
    """Extrae info básica del token sin validar contra DB (rápido)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("user_id"), payload.get("role"), payload.get("sub")
    except Exception as e:
        logger.error(f"Error decodificando token: {e}")
        return None, None

# ---- HELPERS PARA DATOS EXTERNOS ----
async def get_product_details(product_id: int, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{INVENTORY_SERVICE_URL}/api/inventory/products/{product_id}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                # Debug: Ver qué llega realmente
                logger.info(f"📦 Payload recibido para producto {product_id}: {data}") 
                return data
            else:
                logger.warning(f"⚠️ Inventario devolvió {resp.status_code} para ID {product_id}")
                return None
        except Exception as e:
            logger.error(f"Error Inventory: {e}")
            return None

# --- INTEGRACIONES EXTERNAS (HTTP) ---
        
async def get_customer_details(search_term: str, token: str):
    """
    Busca un cliente en CRM por RIF, Email o Nombre.
    Retorna el primer resultado exacto o el más probable.
    """
    if not search_term: return None
    
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CRM_URL}/api/crm/customers?search={search_term}&limit=1", headers=headers)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data:
                    return data[0] # Retornamos el primer cliente encontrado
            return None
        except Exception as e:
            logger.error(f"Error buscando cliente en CRM: {e}")
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
    Obtiene la configuración del tenant.
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

# --- PAGO ---
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

# --- FACTURACIÓN ---

async def get_invoices(
    db: AsyncSession, 
    tenant_id: int,
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Lista facturas con paginación y búsqueda.
    Optimizado para contar IDs en lugar de subqueries.
    """
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

async def create_invoice(
    db: AsyncSession, 
    invoice_data: schemas.InvoiceCreate, 
    tenant_id: int, 
    token: str
) -> models.Invoice:
    """
    Emite una nueva factura de venta.

    Realiza las siguientes acciones en una transacción atómica:
    1. Obtiene datos fiscales de la empresa (Auth) y del cliente (CRM).
    2. Consulta precios y stock de productos en paralelo (Inventory).
    3. Calcula subtotales, impuestos y totales en divisa y moneda local.
    4. Si el método de pago es de contado, registra el pago y marca como PAGADA.
    5. Guarda Snapshots de todos los datos para auditoría fiscal.
    6. Dispara eventos a RabbitMQ para contabilidad e inventario.
    """
    
    # 1. Obtener Datos Externos en Paralelo
    # Lanza las peticiones a microservicios simultáneamente
    tasks = [
        get_tenant_data(token),
        get_customer_details(invoice_data.customer_tax_id, token) if invoice_data.customer_tax_id else asyncio.sleep(0),
        *[get_product_details(item.product_id, token) for item in invoice_data.items]
    ]
    
    results = await asyncio.gather(*tasks)
    
    tenant_data = results[0]
    customer_data = results[1] if invoice_data.customer_tax_id else {}
    product_list = results[2:]
    
    # Mapa de productos
    product_map = {}
    for p in product_list:
        if not p: continue
        
        actual_product = p.get("data", p) if isinstance(p, dict) else p
        
        p_id = actual_product.get("id")
        if p_id is not None:
            try:
                product_map[int(p_id)] = actual_product
            except ValueError:
                # Si el ID no es numérico, se guarda como está
                product_map[p_id] = actual_product
    
    if not tenant_data:
        raise ValueError("Error crítico: No se pudieron obtener datos fiscales de la empresa.")
    
    # 2. Configuración Fiscal y Cambiaria
    settings_q = select(models.FinanceSettings).filter(models.FinanceSettings.tenant_id == tenant_id)
    settings = (await db.execute(settings_q)).scalar_one_or_none()
    tax_rate = settings.tax_rate if settings else Decimal(16.00)
    
    # Obtener Tasa de Cambio
    rate_q = select(models.ExchangeRate).order_by(desc(models.ExchangeRate.acquired_at)).limit(1)
    rate_obj = (await db.execute(rate_q)).scalar_one_or_none()
    exchange_rate = rate_obj.rate if rate_obj else Decimal(1)
    
    # Obtener datos del usuario
    user_sub, user_role, _ = get_user_from_token(token)
    
    # 3. Procesar Items y Totales
    total_base = Decimal(0)
    db_items = []
    db_event_items = []
    
    for item in invoice_data.items:
        product = product_map.get(int(item.product_id))
        if not product:
            raise ValueError(f"Producto ID {item.product_id} no encontrado en Inventario.")
        
        try:
            stock_available = Decimal(str(product.get('stock', 0)))
        except:
            stock_available = Decimal(0)
            
        
        # Validación de Stock
        if stock_available < item.quantity:
            raise ValueError(f"Stock insuficiente para '{product['name']}'. Disponibles: {product['stock']}")
        
        # Precio unitario
        try:
            unit_price = Decimal(str(product.get('price', 0)))
        except:
            unit_price = Decimal(0)
        
        line_total = unit_price * item.quantity
        total_base += line_total
        
        db_items.append(models.InvoiceItem(
            product_id=item.product_id,
            product_name=product['name'],
            quantity=item.quantity,
            unit_price=unit_price,
            total_price=line_total
        ))
        
        db_event_items.append({
            "product_id": item.product_id,
            "quantity": float(item.quantity)
        })

    # Cálculos Finales
    tax_amount = round_money(total_base * (tax_rate / 100))
    total_usd = round_money(total_base + tax_amount)
    total_ves = round_money(total_usd * exchange_rate)
    
    # 4. Determinar Estado Inicial
    status = "ISSUED"
    
    db_payments = []
    if invoice_data.payment and invoice_data.payment.amount > 0:
        paid_amount = invoice_data.payment.amount
        
        # Caso A: Pagó todo
        if paid_amount >= total_usd:
            status = "PAID"
            paid_amount = total_usd
        
        # Caso B: Pagó una parte (Abono / Adelanto)
        else:
            status = "PARTIALLY_PAID"
            
        # Creamos el registro del pago
        db_payments.append(models.Payment(
            amount=paid_amount,
            currency=invoice_data.currency, # Asumimos pago en la misma moneda base
            payment_method=invoice_data.payment.payment_method,
            reference=invoice_data.payment.reference,
            notes=invoice_data.payment.notes,
            created_at=date.today()
        ))
        
    # 5. Numeración
    last_inv_q = select(models.Invoice).filter(models.Invoice.tenant_id == tenant_id).order_by(desc(models.Invoice.invoice_number)).limit(1)
    last_inv = (await db.execute(last_inv_q)).scalar_one_or_none()
    new_number = (last_inv.invoice_number + 1) if last_inv else 1
    
    # 6. Crear Factura
    new_invoice = models.Invoice(
        tenant_id=tenant_id,
        salesperson_id=invoice_data.salesperson_id,
        created_by_user_id=user_sub,
        created_by_role=user_role,
        
        # Datos Fiscales
        invoice_number=new_number,
        control_number=f"00-{new_number:08d}", # Generador simple de control
        status=status,
        
        # Snapshot Empresa 
        company_name=tenant_data.get('name'),
        company_rif=tenant_data.get('rif'),
        company_address=tenant_data.get('address'),
        
        # Snapshot Cliente
        customer_name=customer_data.get('name') or "CLIENTE GENÉRICO",
        customer_rif=customer_data.get('tax_id'),
        customer_email=customer_data.get('email'),
        customer_address=customer_data.get('address'),
        customer_phone=customer_data.get('phone'),
        
        # Totales
        currency=invoice_data.currency,
        exchange_rate=exchange_rate,
        subtotal_usd=total_base,
        tax_amount_usd=tax_amount,
        total_usd=total_usd,
        amount_ves=total_ves,
        
        # Relaciones
        items=db_items,
        payments=db_payments
    )
    
    # Guardado Atómico
    db.add(new_invoice)
    await db.commit()
    
    result_reload = await db.execute(
        select(models.Invoice)
        .options(selectinload(models.Invoice.items), selectinload(models.Invoice.payments))
        .filter(models.Invoice.id == new_invoice.id)
    )
    new_invoice = result_reload.scalars().first()
    
    items_for_event = []
    for i in new_invoice.items:
        items_for_event.append({
            "product_id": i.product_id,
            "product_name": i.product_name,
            "quantity": float(i.quantity),
            "unit_price": float(i.unit_price),  
            "total_price": float(i.total_price)
        })
    
    # 7. Disparar Eventos
    # Evento 1: Factura Creada
    event_data ={
        "id": new_invoice.id,
        "tenant_id": tenant_id,
        "total_amount": float(new_invoice.total_usd),
        "currency": new_invoice.currency,
        "status": new_invoice.status,
        "date": str(new_invoice.created_at),
        "items": items_for_event
    }
    publish_event("invoice.created", event_data)
    
    # Evento 2: Pago Inmediato
    if len(db_payments) > 0:
        paid_event = {
            "invoice_id": new_invoice.id,
            "tenant_id": tenant_id,
            "total_amount": float(db_payments[0].amount),
            "payment_method": db_payments[0].payment_method,
            "paid_at": str(datetime.utcnow()),
            "items": event_data["items"], # Reenviamos items para que Inventory sepa qué descontar
            "origin": "immediate_sale"
        }
        publish_event("invoice.paid", paid_event)
        
    return new_invoice

async def get_invoice_by_id(db: AsyncSession, invoice_id: int, tenant_id: int):
    """Busca una factura por ID con sus items cargados."""
    query = (
        select(models.Invoice)
        .options(selectinload(models.Invoice.items), selectinload(models.Invoice.payments))
        .filter(models.Invoice.id == invoice_id, models.Invoice.tenant_id == tenant_id)
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

async def create_cash_close(
    db: AsyncSession,
    close_data: schemas.CashCloseCreate,
    tenant_id: int,
    user_id: int,
) -> models.CashClose:
    """
    Genera el Cierre de Caja.
    1. Busca facturas PAGADAS o PARCIALMENTE PAGADAS de la empresa que NO tengan cash_close_id.
    2. Suma los pagos asociados a esas facturas para calcular el 'Sistema'.
    3. Compara contra lo 'Declarado' por el usuario.
    4. Cierra las facturas asignándoles el ID del cierre.
    """
    
    # 1. Buscar Facturas Pendientes de Cierre
    # Incluimos ISSUED para cerrar ventas a crédito del día.
    
    stm_invoices = select(models.Invoice).options(
        selectinload(models.Invoice.payments)
    ).filter(
        models.Invoice.tenant_id == tenant_id,
        models.Invoice.created_by_user_id == user_id,
        models.Invoice.status.in_(["PAID", "PARTIALLY_PAID", "ISSUED"]),
        models.Invoice.cash_close_id.is_(None),
        models.Invoice.status != "VOID"
    )
    
    result = await db.execute(stm_invoices)
    invoices = result.scalars().all()
    
    if not invoices:
        raise ValueError("No hay movimientos pendientes para cerrar caja.")
    
    # 2. Inicializar Acumuladores
    summary = {
        "sales_usd": Decimal(0), "tax_usd": Decimal(0),
        "sales_ves": Decimal(0), "tax_ves": Decimal(0),
        
        "cash_usd": Decimal(0), "card_usd": Decimal(0), "transfer_usd": Decimal(0),
        "cash_ves": Decimal(0), "card_ves": Decimal(0), "transfer_ves": Decimal(0),
        
        "cash_ves_equiv": Decimal(0),      
        "card_ves_equiv": Decimal(0),
        "transfer_ves_equiv": Decimal(0),
        
        "credit_usd": Decimal(0), "credit_ves": Decimal(0)
    }
    
    min_date = datetime.utcnow()
    max_date = datetime.utcnow()
    
    if invoices:
        min_date = invoices[-1].created_at
        max_date = invoices[0].created_at
        
    for inv in invoices:
        # Sumar ventas (Base + IVA) para reporte
        summary["sales_usd"] += inv.subtotal_usd
        summary["tax_usd"] += inv.tax_amount_usd
        
        rate = inv.exchange_rate or 1
        summary["sales_ves"] += (inv.subtotal_usd * rate)
        summary["tax_ves"] += (inv.tax_amount_usd * rate)
        
        paid_amount_usd_accum = Decimal(0)
        
        for p in inv.payments:
            # Clasificar por Moneda y Método
            if p.currency == "USD":
                paid_amount_usd_accum += p.amount
                if p.payment_method == "CASH": summary["cash_usd"] += p.amount
                elif p.payment_method in ["ZELLE", "USDT"]: summary["transfer_usd"] += p.amount
                else: summary["card_usd"] += p.amount
            
            if p.currency == "VES":
                if p.payment_method == "CASH": 
                    summary["cash_ves"] += (p.amount * rate)
                    summary["cash_ves_equiv"] += p.amount
                elif p.payment_method in ["DEBIT_CARD", "BIOPAGO"]: 
                    summary["card_ves"] += (p.amount * rate)
                    summary["card_ves_equiv"] += p.amount
                else: 
                    summary["transfer_ves"] += (p.amount * rate) 
                    summary["transfer_ves_equiv"] += p.amount
                
        # Calcular Crédito 
        # Si la factura no está pagada totalmente, el remanente es CxC
        total_paid_usd = paid_amount_usd_accum
        
        if inv.status != "PAID":
            if not inv.payments:
                summary["credit_usd"] += inv.total_usd
                summary["credit_ves"] += (inv.total_usd * rate)
        
    # 3. Crear Objeto Cierre
    cash_close = models.CashClose(
        tenant_id=tenant_id,
        user_id=user_id,
        period_start=min_date,
        period_end=max_date,
        
        # Totales Sistema USD
        total_sales_usd=summary["sales_usd"],
        total_tax_usd=summary["tax_usd"],
        total_cash_usd=summary["cash_usd"],
        total_debit_card_usd=summary["card_usd"],
        total_transfer_usd=summary["transfer_usd"],
        total_credit_sales_usd=summary["credit_usd"],
        
        # Totales Sistema USD
        total_sales_ves=summary["sales_ves"],
        total_tax_ves=summary["tax_ves"],
        total_cash_ves=summary["cash_ves"],
        total_debit_card_ves=summary["card_ves"],
        total_transfer_ves=summary["transfer_ves"],
        total_credit_sales_ves=summary["credit_ves"],
        
        # Declarado
        declared_cash_usd=close_data.declared_cash_usd,
        declared_cash_ves=close_data.declared_cash_ves,
        
        # Diferencias
        # Solo calcula diferencia en EFECTIVO
        difference_usd=close_data.declared_cash_usd - summary["cash_usd"],
        difference_ves=close_data.declared_cash_ves - summary["cash_ves"],
        
        notes=close_data.notes
    )
    
    db.add(cash_close)
    await db.flush()
    
    # 4. Actualizar Facturas
    for inv in invoices:
        inv.cash_close_id = cash_close.id
        db.add(inv)
        
    await db.commit()
    await db.refresh(cash_close)
    
    # 5. Evento para Contabilidad
    event_payload = {
        "tenant_id": tenant_id,
        "cash_close_id": cash_close.id,
        "date": str(cash_close.created_at),
        "summary": {
            # Enviamos ambos para que contabilidad decida
            "total_sales_usd": float(cash_close.total_sales_usd),
            "total_tax_usd": float(cash_close.total_tax_usd),
            "collected_cash_usd": float(cash_close.total_cash_usd),
            "collected_bank_usd": float(cash_close.total_debit_card_usd + cash_close.total_transfer_usd),
            "collected_cash_ves_equiv": float(summary["cash_ves_equiv"]),
            "collected_bank_ves_equiv": float(summary["card_ves_equiv"] + summary["transfer_ves_equiv"]),
            "sales_on_credit_usd": float(cash_close.total_credit_sales_usd)
        }
    }
    
    publish_event("finance.cash_close_created", event_payload)
    
    return cash_close

# --- GESTION DE COTIZACIONES ---
async def get_next_quote_number(db: AsyncSession, tenant_id: int) -> str:
    """Genera el siguiente número correlativo para cotizaciones (Ej: COT-00005)."""
    query = select(models.Quote.id).filter(models.Quote.tenant_id == tenant_id).order_by(desc(models.Quote.id)).limit(1)
    result = await db.execute(query)
    last_id = result.scalar() or 0
    return f"COT-{last_id + 1:05d}"

async def create_quote(db: AsyncSession, quote_in: schemas.QuoteCreate, tenant_id: int, token: str) -> models.Quote:
    """
    Registra una nueva cotización en el sistema.
    
    Consulta precios de productos en inventario y datos del cliente en CRM.
    """
    # Datos Usuario y Tenant
    _, _, user_email = get_user_from_token(token)
    tenant_data = await get_tenant_data(token)
    
    # Datos Cliente
    customer = await get_customer_details(quote_in.customer_tax_id, token)
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

async def get_quotes(
    db: AsyncSession,
    tenant_id: int,
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None
):
    """Lista las cotizaciones con filtros."""
    offset = (page - 1) * limit
    conditions = [models.Quote.tenant_id == tenant_id]
    
    if search:
        search_term = f"%{search}%"
        conditions.append(
            or_(
                models.Quote.customer_name.ilike(search_term),
                models.Quote.customer_rif.ilike(search_term),
                cast(models.Quote.quote_number, String).ilike(search_term)
            )
        )
    
    # Contar Rapido
    count_query = select(func.count(models.Quote.id)).filter(*conditions)
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0
    
    # Consulta de Datos
    query = (
        select(models.Quote)
        .options(selectinload(models.Quote.items))
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
async def get_sales_total_by_employee(db: AsyncSession, tenant_id: int, employee_id: int, start_date: date, end_date: date) -> Decimal:
    """
    Suma el subtotal_usd de las facturas validas de un vendedor.
    """
    stmt = select(func.sum(models.Invoice.subtotal_usd)).where(
        and_(
            models.Invoice.tenant_id == tenant_id,
            models.Invoice.salesperson_id == employee_id,
            models.Invoice.status.in_(["PAID"]),
            func.date(models.Invoice.created_at) >= start_date,
            func.date(models.Invoice.created_at) <= end_date
        )
    )
    result = await db.execute(stmt)
    total = result.scalar()
    
    return total if total is not None else Decimal(0)

async def get_dashboard_metrics(db: AsyncSession, tenant_id: int):
    """Calcula KPIs del día."""
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
    """Compara ventas mes a mes (Año actual vs Año anterior)."""
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