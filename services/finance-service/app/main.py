from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .database import get_db, engine, SyncSessionLocal
from contextlib import asynccontextmanager
import logging
import pika
import json
# Planificador
from apscheduler.schedulers.background import BackgroundScheduler
from . import crud, schemas, database, models
from .services import exchange
from .security import get_current_user_email

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finance-service")

# --- Función del Scheduler ---
def run_exchange_rate_job():
    """
    Ejecuta la actualización de la tasa usando una conexión síncrona.
    """
    logger.info("⏰ [SCHEDULER] Iniciando trea de tasa cambiaria...")
    
    # Creamos una sesión síncrona nueva solo para esta tarea
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
    
    # Crear tablas (Async)
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
        
    # Iniciar el Scheduler (Reloj)
    scheduler = BackgroundScheduler()
    
    # Ejecutar cada 6 horas.
    scheduler.add_job(run_exchange_rate_job, 'interval', hours=6)
    
    # Se ejecuta inmediatamente al arrancar para tener datos ya
    scheduler.add_job(run_exchange_rate_job)
    
    scheduler.start()
    logger.info("⏰ Scheduler iniciado.")
    
    yield # Corre la aplicación
    
    # Apagado
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

# --- Configuración de RAbbitMQ --- 
def publish_invoice_created(invoice_data: dict):
    try:
        # Contectar a RabbitMQ
        connection = pika.BlockingConnection(pika.URLParameters('amqp://guest:guest@rabbitmq:5672/%2F'))
        channel = connection.channel()
        
        # Asegurar que la cola existe (para no enviar al vacío)
        channel.queue_declare(queue='invoice_events', durable=True)
        
        # Publicar el mensaje
        channel.basic_publish(
            exchange='',
            routing_key='invoice_events',
            body=json.dumps(invoice_data),
            properties=pika.BasicProperties(
                delivery_mode=2, # Mensaje persiste (no se pierde si Rabbit reinicia)
            )
        )
        connection.close()
        logger.info(f"📢 Evento enviado a RabbitMQ: {invoice_data}")
        
    except Exception as e:
        logger.error(f"❌ Error conectado a RabbitMQ: {e}")
        
# --- Eventos de Inicio ---
@app.on_event("startup")
async def startup():
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
        
# --- Endpoints ---
@app.post("/invoices", response_model=schemas.InvoiceResponse)
async def create_invoice(invoice: schemas.InvoiceCreate, db: AsyncSession = Depends(database.get_db), current_user_email: str = Depends(get_current_user_email)):
    # Guardar en DB
    new_invoice = await crud.create_invoice(db, invoice, owner_email=current_user_email)
    
    # Convertir a diccionario para enviar
    invoice_dict = {
        "id": new_invoice.id,
        "amount": str(new_invoice.amount), 
        "currency": new_invoice.currency,
        "customer_email": new_invoice.customer_email
    }
    
    # Enviar evento a RabbitMQ
    publish_invoice_created(invoice_dict)
    
    return new_invoice

@app.get("/invoices", response_model=list[schemas.InvoiceResponse])
async def read_invoices(db: AsyncSession = Depends(database.get_db), current_user_email: str = Depends(get_current_user_email)):
    # --- LOG DE DEPURACIÓN ---
    logger.info(f"🕵️‍♂️ Petición de facturas recibida.")
    logger.info(f"👤 Usuario identificado en el Token: '{current_user_email}'")
    # -------------------------
    
    facturas = await crud.get_invoices(db, owner_email=current_user_email)
    
    logger.info(f"📦 Facturas encontradas para {current_user_email}: {len(facturas)}")
    return facturas

# --- Consultar Tasa ---
@app.get("/exchange-rate")
async def get_current_rate(db: AsyncSession = Depends(database.get_db)):
    """Devuelve la última tasa conocida registrada en la Base de Datos."""
    # Consultamos la tabla ExchangeRate, ordenamos por fecha descendente y tomamos la primera
    query = select(models.ExchangeRate).order_by(models.ExchangeRate.acquired_at.desc()).limit(1)
    result = await db.execute(query)
    rate = result.scalars().first()
    
    if not rate:
        return {
            "status": "No data",
            "message": "Aún no hay tasas registradas. Espera que el Scheduler ejecute la tarea."
        }
        
    return {
        "currency_from": rate.currency_from,
        "currency_to": rate.currency_to,
        "rate": rate.rate,
        "source": rate.source,
        "acquired_at": rate.acquired_at
    }