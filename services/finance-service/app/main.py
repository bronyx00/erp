from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from contextlib import asynccontextmanager
from typing import Optional
from datetime import date, datetime, time
import logging

# Scheduler
from apscheduler.schedulers.background import BackgroundScheduler

# Imports Locales
from . import crud, schemas, database, models
from .services import exchange
from .database import engine, SyncSessionLocal
from .events import publish_event

# Imports Comunes
from erp_common.security import oauth2_scheme, RequirePermission, Permissions, UserPayload
from .schemas import (PaginatedResponse, InvoiceSummary, SalesTotalResponse, FinanceSettingsRead, InvoiceResponse)
from .utils.pdf_generator import generate_invoice_pdf

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finance-service")

# --- SCHEDULER (Segundo Plano) ---
def run_exchange_rate_job():
    """Tarea programada para actualizar la tasa del BCV."""
    logger.info("⏰ [SCHEDULER] Iniciando tarea de tasa cambiaria...")
    try:
        with SyncSessionLocal() as db:
            exchange.fetch_and_store_rate(db)
            logger.info("⏰ [SCHEDULER] Tarea finalizada con éxito.")
    except Exception as e:
        logger.error(f"❌ [SCHEDULER] Falló la tarea: {e}")
    

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Crear tablas al inicio
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
        
    # 2. Iniciar el Scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_exchange_rate_job, 'interval', hours=6)
    scheduler.add_job(run_exchange_rate_job) # Ejecutar ya al inicio
    scheduler.start()
    logger.info("⏰ Scheduler iniciado.")
    
    yield 
    
    # 3. Apagado
    scheduler.shutdown()

# --- Configuración de FastAPI ---
app = FastAPI(
    title="Finance Service",
    description="Módulo de Facturación, Cotizaciones y Control Financiero.",
    version="1.0.0",
    root_path="/api/finance",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ENDPOINTS ---
@app.get("/invoices", response_model=PaginatedResponse[InvoiceSummary])
async def read_invoices(
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None,
    start_date: date = None,
    end_date: date = None,
    db: AsyncSession = Depends(database.get_db), 
    user: UserPayload = Depends(RequirePermission(Permissions.INVOICE_READ))
):
    """
    Lista facturas con visibilidad basada en roles.
    """
    # Definir Roles con privilegios
    MANAGERS = ["OWNER", "ADMIN", "SALES_SUPERVISOR"]
    
    filter_user_id = None
    filter_pending_close = False
    filter_start = None
    filter_end = None
    
    if start_date:
        filter_start = datetime.combine(start_date, time.min)
        
    if end_date:
        filter_end = datetime.combine(end_date, time.max)
    elif start_date:
        filter_end = datetime.combine(start_date, time.max)

    if user.role not in MANAGERS:
        # Empleados solo ven sus facturas abiertas
        filter_user_id = user.user_id
        filter_pending_close = True
    
    return await crud.get_invoices(
        db, 
        tenant_id=user.tenant_id, 
        page=page, 
        limit=limit, 
        status=status, 
        search=search,
        created_by_id=filter_user_id,
        only_pending_close=filter_pending_close,
        date_start=filter_start,
        date_end=filter_end
    )

@app.get("/invoices/{invoice_id}", response_model=schemas.InvoiceResponse)
async def get_invoice_by_id(
    invoice_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.INVOICE_READ))
):
    """
    Obtiene factura por su ID
    """
    return await crud.get_invoice_by_id(db, invoice_id=invoice_id, tenant_id=user.tenant_id)

@app.post("/invoices", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    invoice: schemas.InvoiceCreate, 
    db: AsyncSession = Depends(database.get_db), 
    user: UserPayload = Depends(RequirePermission(Permissions.INVOICE_CREATE)),
    token: str = Depends(oauth2_scheme)
):
    """
    **Emitir Factura**
    
    Crea una nueva factura de venta. 
    Se comunica con el servicio de Inventario para verificar items y precios (opcional).
    Envía un evento a RabbitMQ (`invoice.created`) al finalizar.
    """
    new_invoice = await crud.create_invoice(db, invoice, tenant_id=user.tenant_id, token=token)
    
    invoice_dict = {
        "id": new_invoice.id,
        "amount": str(new_invoice.total_usd),
        "total_usd": str(new_invoice.total_usd),
        "currency": new_invoice.currency,
        "customer_rif": new_invoice.customer_rif,
        "items": [{"product_id": i.product_id, "quantity": i.quantity} for i in new_invoice.items]
    }
    publish_event("invoice.created", invoice_dict)
    
    return new_invoice

@app.get("/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.INVOICE_READ))
):
    """
    **Descargar PDF de Factura**
    
    Genera un PDF en formato ticket (térmico) para imprimir.
    Retorna un stream de bytes (application/pdf).
    """
    invoice = await crud.get_invoice_by_id(db, invoice_id, user.tenant_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    pdf_buffer = generate_invoice_pdf(invoice_data=invoice, items=invoice.items)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=factura_{invoice.id}.pdf"}
    )
    
@app.post("/invoices/{invoice_id}/void", response_model=schemas.InvoiceResponse)
async def void_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.INVOICE_VOID))
):
    """
    **Anular Factura**
    
    Marca una factura como ANULADA (VOID) y dispara un evento para revertir
    el inventario y la contabilidad.
    """
    try: 
        invoice = await crud.set_invoice_void(db, invoice_id, user.tenant_id)
        
        event_data = {
            "invoice_id": invoice.id,
            "tenant_id": user.tenant_id,
            "items": [{"product_id": i.product_id, "quantity": i.quantity} for i in invoice.items]
        }
        publish_event("invoice.voided", event_data)
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- PAGOS ---
@app.post("/payments", response_model=schemas.PaymentResponse)
async def create_payment(
    payment: schemas.PaymentCreate, 
    db: AsyncSession = Depends(database.get_db), 
    user: UserPayload = Depends(RequirePermission(Permissions.PAYMENT_CREATE))
):
    """
    **Registrar Pago (Abono)**
    
    Registra un pago parcial o total a una factura existente.
    Si el saldo llega a 0, actualiza el estado de la factura a PAID.
    """
    try:
        new_payment, invoice, is_fully_paid = await crud.create_payment(db, payment, tenant_id=user.tenant_id)
        
        if is_fully_paid:
            event_data = {
                "invoice_id": invoice.id,
                "tenant_id": user.tenant_id,
                "total_amount": float(invoice.total_usd),
                "paid_at": str(new_payment.created_at),
                "items": [{"product_id": item.product_id, "quantity": item.quantity} for item in invoice.items]
            }
            publish_event("invoice.paid", event_data)
        
        return new_payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# --- CIERRE DE CAJA ---
@app.post("/cash-close", response_model=schemas.CashCloseResponse)
async def perform_cash_close(
    close_data: schemas.CashCloseCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.INVOICE_CREATE))
):
    """
    Realiza Cierre de Caja
    
    1. Agrupa todas las facturas abiertas/pendientes de cierre.
    2. Calcula los totales en USD y VES según los pagos registrados.
    3. Compara con el efectivo declarado por el usuario.
    4. Genera el asiento contable global.
    """
    try:
        user_id_int = int(user.user_id) if user.user_id else 0
        
        return await crud.create_cash_close(db, close_data, user.tenant_id, user_id_int)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- COTIZACIONES ---
@app.post("/quotes", response_model=schemas.QuoteResponse)
async def create_quote_endpoint(
    quote: schemas.QuoteCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.QUOTE_CREATE)),
    token: str = Depends(oauth2_scheme)
):
    """
    **Crear Cotización**
    
    Genera un presupuesto para un cliente. No afecta inventario ni contabilidad
    hasta que se convierta en factura.
    """
    return await crud.create_quote(db, quote, user.tenant_id, token)

@app.get("/quotes", response_model=PaginatedResponse[schemas.QuoteResponse])
async def list_quotes(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.QUOTE_READ))
):
    """
    **Listar Cotizaciones**
    
    Muestra el historial de presupuestos emitidos.
    """
    return await crud.get_quotes(db, tenant_id=user.tenant_id, page=page, limit=limit, search=search, status=status)

@app.post("/quotes/{quote_id}/convert", response_model=schemas.InvoiceResponse)
async def convert_quote(
    quote_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.QUOTE_CREATE)),
    token: int = Depends(oauth2_scheme)
):
    """
    **Convertir a Factura**
    
    Transforma una cotización existente en una factura real, copiando todos sus datos.
    Marca la cotización como FACTURADA (INVOICED).
    """
    try:
        invoice = await crud.convert_quote_to_invoice(db, quote_id, user.tenant_id, token)
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- CONFIGURACIÓN Y TASAS ---
@app.get("/settings", response_model=FinanceSettingsRead)
async def read_settings(
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.INVOICE_READ))
):
    """
    Obtiene la configuración financiera.
    """
    return await crud.get_finance_settings(db, user.tenant_id)

@app.get("/exchange-rate")
async def get_current_rate(db: AsyncSession = Depends(database.get_db)):
    """Obtiene la última tasa de cambio registrada en el sistema."""
    query = select(models.ExchangeRate).order_by(models.ExchangeRate.acquired_at.desc()).limit(1)
    result = await db.execute(query)
    rate = result.scalars().first()
    
    if not rate:
        return {"status": "No data", "message": "Aún no hay tasas registradas."}
        
    return {
        "currency_from": rate.currency_from,
        "currency_to": rate.currency_to,
        "rate": rate.rate,
        "source": rate.source,
        "acquired_at": rate.acquired_at
    }
    
# --- REPORTES ---

@app.get("/reports/dashboard", response_model=schemas.DashboardMetrics)
async def get_dashboard_metrics(
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.REPORTS_VIEW))
):
    """Métricas KPI para el dashboard principal."""
    return await crud.get_dashboard_metrics(db, user.tenant_id)

@app.get("/reports/sales-by-method", response_model=list[schemas.SalesReportItem])
async def get_sales_report_by_method(
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.REPORTS_VIEW))
):
    """Reporte agrupado de ventas por método de pago."""
    return await crud.get_sales_report_by_method(db, user.tenant_id)

@app.get("/sales-over-time", response_model=list[schemas.SalesDataPoint])
async def read_sales_over_time(
    db: AsyncSession = Depends(database.get_db), 
    user: UserPayload = Depends(RequirePermission(Permissions.REPORTS_VIEW))
):
    """Gráfico comparativo de ventas Año Actual vs Año Anterior."""
    return await crud.get_sales_compatison(db, user.tenant_id)

@app.get("/reports/sales-total", response_model=SalesTotalResponse)
async def get_sales_total_for_payroll(
    employee_id: int,
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.REPORTS_VIEW))
):
    """
    **[INTERNO] Total Ventas por Empleado**
    
    Endpoint consumido por el servicio de HHRR para calcular comisiones de nómina.
    """
    total_sales = await crud.get_sales_total_by_employee(db, tenant_id=user.tenant_id, employee_id=employee_id, start_date=start_date, end_date=start_date)
    
    return {
        "tenant_id": user.tenant_id,
        "employee_id": employee_id,
        "total_sales_usd": total_sales,
        "period_start": start_date,
        "period_end": end_date
    }


