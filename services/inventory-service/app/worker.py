import pika
import json
import os
import time
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import DATABASE_URL

# Configuración de RabbitMQ
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F")

# Configuración DB Síncrona
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def update_stock(items, action="decrease"):
    """
    Descuenta el stock de los productos vendidos.
    action: 'decrease' (venta) o 'increase' (devolucion)
    """
    db = SessionLocal()
    try:
        print(f"📦 Actualizando stock ({action})...")
        for item in items:
            product_id = item['product_id']
            qty = item['quantity']
            
            if action == "decrease":
                stmt = text("UPDATE products SET stock = stock - :qty WHERE id = :pid")
            else: # increase
                stmt = text("UPDATE products SET stock = stock + :qty WHERE id = :pid")
                
            db.execute(stmt, {"qty": qty, "pid": product_id})
            print(f"   Product {product_id}: {action} {qty}")
        db.commit()
    except Exception as e:
        print(f"❌ Error stock: {e}")
        db.rollback()
    finally:
        db.close()
        
def callback(ch, method, properties, body):
    """Procesa el evento recibido de RabbitMQ"""
    print(f"📥 [Inventory] Evento recibido: {method.routing_key}")
    try:
        message = json.loads(body)
        items = message.get("items") or message.get("data", {}).get("items")
        
        if items:
            if method.routing_key == "invoice.paid":
                update_stock(items, action="decrease")
            elif method.routing_key == "invoice.voided":
                update_stock(items, action="increase")
            else:
                print(f"⚠️ Evento desconocido: {method.routing_key}")
        else:
            print("⚠️ El evento no contenía items.")
            
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"❌ Error: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
def start_worker():
    print("⏳ [Inventory Worker] Conectando a RabbitMQ...")
    connection = None
    
    # Lógica de reintento
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            break
        except pika.exceptions.AMQPConnectionError:
            print("     Reintentando conexión en 5s...")
            time.sleep(5)
            
    channel = connection.channel()

    channel.exchange_declare(exchange='erp_events', exchange_type='topic', durable=True)
    
    # Cola exclusiva para inventario
    result = channel.queue_declare(queue='inventory_stock_updates', durable=True)
    queue_name = result.method.queue
    
    # Escucha específicamente "invoice.paid"
    channel.queue_bind(exchange='erp_events', queue=queue_name, routing_key='invoice.paid')
    channel.queue_bind(exchange="erp_events", queue=queue_name, routing_key='invoice.voided')
    
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)
    
    print("🎧 [Inventory Worker] Escuchando eventos de ventas (invoice.paid)...")
    channel.start_consuming()
    
if __name__ == "__main__":
    start_worker()