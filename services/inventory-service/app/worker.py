import pika
import json
import os
import time
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ajuste de path para importar app.database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import DATABASE_URL

# Configuración de RabbitMQ
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F")

# Configuración DB Síncrona
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def update_stock(items, action="decrease"):
    """Descuenta o repone el stock de los productos."""
    db = SessionLocal()
    try:
        print(f"📦 [Inventory] Actualizando stock ({action})...", flush=True)
        for item in items:
            product_id = item['product_id']
            qty = item['quantity']
            
            if action == "decrease":
                stmt = text("UPDATE products SET stock = stock - :qty WHERE id = :pid")
            else: # increase (anulación)
                stmt = text("UPDATE products SET stock = stock + :qty WHERE id = :pid")
                
            db.execute(stmt, {"qty": qty, "pid": product_id})
            print(f"   -> Producto {product_id}: {action} {qty}", flush=True)
        db.commit()
    except Exception as e:
        print(f"❌ [Inventory] Error actualizando stock: {e}", flush=True)
        db.rollback()
    finally:
        db.close()
        
def callback(ch, method, properties, body):
    print(f"📥 [Inventory] Evento recibido: {method.routing_key}", flush=True)
    try:
        message = json.loads(body)
        # Soporte para items directos o dentro de 'data'
        items = message.get("items") or message.get("data", {}).get("items")
        
        if items:
            if method.routing_key == "invoice.paid":
                update_stock(items, action="decrease")
            elif method.routing_key == "invoice.voided":
                update_stock(items, action="increase")
            else:
                print(f"⚠️ Evento no manejado: {method.routing_key}", flush=True)
        else:
            print("⚠️ El evento no contenía items para procesar.", flush=True)
            
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}", flush=True)
        ch.basic_ack(delivery_tag=method.delivery_tag) # Ack para no bloquear la cola, aunque falle
        
def start_worker():
    print("⏳ [Inventory Worker] Iniciando...", flush=True)
    connection = None
    
    # Bucle de Espera Inteligente (Solución al log repetitivo)
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            print("✅ [Inventory Worker] Conectado a RabbitMQ", flush=True)
            break
        except (pika.exceptions.AMQPConnectionError, OSError) as e:
            print(f"⚠️ RabbitMQ no listo. Reintentando en 5s... ({e})", flush=True)
            time.sleep(5)
            
    channel = connection.channel()
    channel.exchange_declare(exchange='erp_events', exchange_type='topic', durable=True)
    
    # Cola exclusiva
    result = channel.queue_declare(queue='inventory_stock_updates', durable=True)
    queue_name = result.method.queue
    
    channel.queue_bind(exchange='erp_events', queue=queue_name, routing_key='invoice.paid')
    channel.queue_bind(exchange='erp_events', queue=queue_name, routing_key='invoice.voided')
    
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)
    
    print("🎧 [Inventory Worker] Escuchando...", flush=True)
    channel.start_consuming()
    
if __name__ == "__main__":
    start_worker()