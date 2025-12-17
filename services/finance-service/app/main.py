from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from .database import engine, SyncSessionLocal
from contextlib import asynccontextmanager
import logging
import pika
import json
import os
# Planificador
from apscheduler.schedulers.background import BackgroundScheduler
from . import crud, schemas, database, models
from .services import exchange
from .security import get_current_tenant_id, oauth2_scheme, SECRET_KEY, ALGORITHM, RequirePermission, Permissions, UserPayload
from .schemas import PaginatedResponse, InvoiceSummary
from .utils.pdf_generator import generate_invoice_pdf
from jose import jwt, JWTError

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finance-service")

# --- Función del Scheduler ---
def run_exchange_rate_job():
    """
    Ejecuta la actualización de la tasa usando una conexión síncrona.
    """
    logger.info("⏰ [SCHEDULER] Iniciando tarea de tasa cambiaria...")
    try:
        with SyncSessionLocal() as db:
            exchange.fetch_and_store_rate(db)
            logger.info("⏰ [SCHEDULER] Tarea finalizada con éxito.")
    except Exception as e:
        logger.error(f"❌ [SCHEDULER] Falló la tarea: {e}")
    
# --- Ciclo de Vida de la App (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando Finance Service...")
    
    # 1. Crear tablas (Si no existen, como respaldo)
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
        
    # 2. Iniciar el Scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_exchange_rate_job, 'interval', hours=6)
    scheduler.add_job(run_exchange_rate_job) # Ejecutar ya al inicio
    scheduler.start()
    logger.info("⏰ Scheduler iniciado.")
    
    # --- ¡ESTA LÍNEA ES CRÍTICA! ---
    yield 
    # -------------------------------
    
    # 3. Apagado
    scheduler.shutdown()
    logger.info("🛑 Finance Service detenido.")

# --- Configuración de FastAPI ---
app = FastAPI(title="Finance Service", root_path="/api/finance", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuración de RabbitMQ --- 
def publish_event(routing_key: str, data: dict):
    try:
        url = os.getenv("RABBITMQ_URL", 'amqp://guest:guest@rabbitmq:5672/%2F')
        connection = pika.BlockingConnection(pika.URLParameters(url))
        channel = connection.channel()
        channel.exchange_declare(exchange='erp_events', exchange_type='topic', durable=True)
        channel.basic_publish(
            exchange='erp_events',
            routing_key=routing_key,
            body=json.dumps(data),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        logger.info(f"📢 Evento publicado: {routing_key}")
    except Exception as e:
        logger.error(f"❌ Error publicando evento {routing_key}: {e}")

# --- Endpoints ---
@app.post("/invoices", response_model=schemas.InvoiceResponse)
async def create_invoice(
    invoice: schemas.InvoiceCreate, 
    db: AsyncSession = Depends(database.get_db), 
    user: UserPayload = Depends(RequirePermission(Permissions.INVOICE_CREATE)),
    token: str = Depends(oauth2_scheme)
):
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

@app.post("/payments", response_model=schemas.PaymentResponse)
async def create_payment(
    payment: schemas.PaymentCreate, 
    db: AsyncSession = Depends(database.get_db), 
    user: UserPayload = Depends(RequirePermission(Permissions.PAYMENT_CREATE))
):
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
    
@app.get("/invoices", response_model=PaginatedResponse[InvoiceSummary])
async def read_invoices(
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(database.get_db), 
    user: UserPayload = Depends(RequirePermission(Permissions.INVOICE_READ))
):
    return await crud.get_invoices(db, tenant_id=user.tenant_id, page=page, limit=limit, status=status, search=search)

# --- COTIZACIONES ---
@app.post("/quotes", response_model=schemas.QuoteResponse)
async def create_quote_endpoint(
    quote: schemas.QuoteCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.QUOTE_CREATE)),
    token: str = Depends(oauth2_scheme)
):
    return await crud.create_quote(db, quote, user.tenant_id, token)

@app.get("/quotes", response_model=PaginatedResponse[schemas.QuoteResponse])
async def list_quotes(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.QUOTE_READ))
):
    return await crud.get_quotes(db, tenant_id=user.tenant_id, page=page, limit=limit)

@app.post("/quotes/{quote_id}/convert", response_model=schemas.InvoiceResponse)
async def convert_quote(
    quote_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.QUOTE_CREATE)),
    token: int = Depends(oauth2_scheme)
):
    try:
        invoice = await crud.convert_quote_to_invoice(db, quote_id, user.tenant_id, token)
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/exchange-rate")
async def get_current_rate(db: AsyncSession = Depends(database.get_db)):
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

@app.post("/invoices/{invoice_id}/void", response_model=schemas.InvoiceResponse)
async def void_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.INVOICE_VOID))
):
    invoice = await crud.get_invoice_by_id(db, invoice_id, user.tenant_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    if invoice.status == "VOID":
        raise HTTPException(status_code=400, detail="La factura ya está anulada")
        
    invoice = await crud.set_invoice_void(db, invoice)
    
    event_data = {
        "invoice_id": invoice.id,
        "tenant_id": user.tenant_id,
        "items": [{"product_id": i.product_id, "quantity": i.quantity} for i in invoice.items]
    }
    publish_event("invoice.voided", event_data)
    return invoice

@app.get("/reports/sales-by-method", response_model=list[schemas.SalesReportItem])
async def get_sales_report_by_method(
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.REPORTS_VIEW))
):
    return await crud.get_sales_report_by_method(db, user.tenant_id)

@app.get("/reports/dashboard", response_model=schemas.DashboardMetrics)
async def get_dashboard_metrics(
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.REPORTS_VIEW))
):
    return await crud.get_dashboard_metrics(db, user.tenant_id)


@app.get("/sales-over-time", response_model=list[schemas.SalesDataPoint])
async def read_sales_over_time(
    db: AsyncSession = Depends(database.get_db), 
    user: UserPayload = Depends(RequirePermission(Permissions.REPORTS_VIEW))
):
    return await crud.get_sales_compatison(db, user.tenant_id)

@app.get("/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.INVOICE_READ))
):
    invoice = await crud.get_invoice_by_id(db, invoice_id, user.tenant_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    pdf_buffer = generate_invoice_pdf(invoice_data=invoice, items=invoice.items)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=factura_{invoice.id}.pdf"}
    )