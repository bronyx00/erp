from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import logging
import pika
import json
import threading
# Planificador
from apscheduler.schedulers.background import BackgroundScheduler
from . import crud, schemas, database, models
from .services import exchange

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finance-service")

# --- Función auxiliar para el Scheduler ---
def run_exchange_rate_job():
    """
    Esta función crea una sesión de DB propia (Síncrona)
    y llama a la lógica de actualización.
    """
    # Creamos una sesión manual porque estamos fuera del contexto de una petición HTTP
    # Usamos el engine síncrono que podríamos crear, o un truco simple:
    # Nota: Para producción real con Async, a veces es mejor tener un engine síncrono separado
    # para tareas de fondo. Por simplicidad MVP, usaremos un bloque try/except básico.
    pass 
    # [COMENTARIO] Para no complicar la configuración de DB (mezclar async/sync),
    # en este paso simplemente loguearemos que el scheduler funciona.
    # Integrar SQLAlchemy Sync con Async requiere dos engines. 
    logger.info("⏰ [SCHEDULER] Ejecutando tarea programada de Tasa de Cambio...")
    
    # En una implementación final, aquí crearías:
    # with SyncSessionLocal() as db:
    #     exchange.fetch_and_store_rate(db)
    
# --- Ciclo de Vida de la App (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicio: Crear tablas
    logger.info("🚀 Iniciando Finance Service...")
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
        
    # Inicio: Arrancar el Scheduler (Reloj)
    scheduler = BackgroundScheduler()
    # Ejecutar cada 6 horas.
    scheduler.add_job(run_exchange_rate_job, 'interval', hours=6)
    scheduler.start()
    logger.info("⏰ Scheduler iniciado (Actualización cada 6 horas)")
    
    yield # Corre la aplicación
    
    # Apagado
    scheduler.shutdown()
    logger.info("🛑 Finance Service detenido.")

# --- Configuración de FastAPI ---
app = FastAPI(title="Finance Service", root_path="/api/finance")

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
async def create_invoice(invoice: schemas.InvoiceCreate, db: AsyncSession = Depends(database.get_db)):
    # Guardar en DB
    new_invoice = await crud.create_invoice(db, invoice)
    
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
async def read_invoices(db: AsyncSession = Depends(database.get_db)):
    return await crud.get_invoices(db)

# --- Consultar Tasa ---
@app.get("/exchange-rate")
async def get_current_rate():
    """Devuelve la última tasa conocida"""
    # result = await db.execute(select(models.ExchangeRate).order_by(models.ExchangeRate.acquired_at.desc()))
    # return result.scalars().first()
    return {
        "currency": "VES",
        "rate": 250.50, # Simulado hasta conectar DB síncrona
        "source": "Simulado",
        "status": "Scheduler activo en logs"
    }