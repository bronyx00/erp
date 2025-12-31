import asyncio
import os
import json
import sys
import aio_pika
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# Ajuste de path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import DATABASE_URL

# Configuración
RABBITMQ_URL = os.getenv("RABBITMQ_URL")
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

# Motor DB Síncrono para las operaciones de escritura
engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

@retry(
    stop=stop_after_attempt(15), 
    wait=wait_fixed(5),
    retry=retry_if_exception_type(Exception)
)
async def get_rabbitmq_connection():
    print(f"⏳ [Inventory] Conectando a RabbitMQ...", flush=True)
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    print(f"✅ [Inventory] Conectado exitosamente.", flush=True)
    return connection

def update_stock(items, action="decrease"):
    """Actualiza el stock en la DB de forma atómica"""
    with SessionLocal() as db:
        try:
            print(f"📦 Procesando stock ({action})...", flush=True)
            for item in items:
                sign = '-' if action == 'decrease' else '+'
                # Usamos SQL nativo para velocidad
                stmt = text(f"UPDATE products SET stock = stock {sign} :qty WHERE id = :pid")
                db.execute(stmt, {"qty": item['quantity'], "pid": item['product_id']})
            db.commit()
            print("✅ Stock actualizado.", flush=True)
        except Exception as e:
            print(f"❌ Error DB: {e}", flush=True)
            db.rollback()

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            body = json.loads(message.body)
            routing_key = message.routing_key
            
            # Soporte para estructura plana o anidada en 'data'
            items = body.get("items") or body.get("data", {}).get("items")
            
            if items:
                if routing_key == "invoice.paid":
                    update_stock(items, action="decrease")
        except Exception as e:
            print(f"❌ Error procesando mensaje: {e}", flush=True)

async def main():
    connection = await get_rabbitmq_connection()
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange('erp_events', aio_pika.ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue('inventory_stock_updates', durable=True)
        
        await queue.bind(exchange, routing_key='invoice.paid')
        
        print("🎧 [Inventory] Escuchando eventos...", flush=True)
        await queue.consume(process_message)
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass