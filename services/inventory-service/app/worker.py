import pika
import json
import os
import time
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ajuste de path para poder importar app.database desde el directorio padre
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import DATABASE_URL

# Configuración de RabbitMQ
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F")

# Configuración DB Síncrona (SQLAlchemy Core)
# Reemplazamos el driver asíncrono (+asyncpg) por el estándar para el worker
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

# Motor de Base de Datos
engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def update_stock(items, action="decrease"):
    """
    Actualiza el stock de los productos.
    action: 'decrease' (venta) o 'increase' (devolución/anulación)
    """
    db = SessionLocal()
    try:
        print(f"📦 [Inventory] Procesando actualización de stock ({action})...", flush=True)
        
        for item in items:
            product_id = item['product_id']
            qty = item['quantity']
            
            if action == "decrease":
                # Restar stock (Venta)
                stmt = text("UPDATE products SET stock = stock - :qty WHERE id = :pid")
            else: 
                # Sumar stock (Anulación/Devolución)
                stmt = text("UPDATE products SET stock = stock + :qty WHERE id = :pid")
                
            db.execute(stmt, {"qty": qty, "pid": product_id})
            print(f"   -> Producto ID {product_id}: {action} {qty} unidades", flush=True)
            
        db.commit()
        print("✅ [Inventory] Stock actualizado correctamente.", flush=True)
        
    except Exception as e:
        print(f"❌ [Inventory] Error actualizando stock: {e}", flush=True)
        db.rollback()
    finally:
        db.close()
        
def callback(ch, method, properties, body):
    """Callback que se ejecuta al recibir un mensaje de RabbitMQ"""
    print(f"📥 [Inventory] Evento recibido: {method.routing_key}", flush=True)
    
    try:
        message = json.loads(body)
        # El mensaje puede venir directo o envuelto en 'data' dependiendo del emisor
        items = message.get("items") or message.get("data", {}).get("items")
        
        if items:
            if method.routing_key == "invoice.paid":
                update_stock(items, action="decrease")
            elif method.routing_key == "invoice.voided":
                update_stock(items, action="increase")
            else:
                print(f"⚠️ Evento no manejado por inventario: {method.routing_key}", flush=True)
        else:
            print("⚠️ El evento recibido no contenía lista de ítems.", flush=True)
            
        # Confirmar procesamiento exitoso (Ack)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}", flush=True)
        # Confirmamos igual para no bloquear la cola con un mensaje "venenoso"
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
def start_worker():
    print("⏳ [Inventory Worker] Iniciando servicio...", flush=True)
    connection = None
    
    # --- BUCLE DE ESPERA INTELIGENTE (Retry Loop) ---
    while True:
        try:
            # Intentamos conectar a RabbitMQ
            parameters = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(parameters)
            print("✅ [Inventory Worker] Conectado exitosamente a RabbitMQ", flush=True)
            break
        except (pika.exceptions.AMQPConnectionError, OSError) as e:
            # Capturamos fallos de conexión y DNS
            print(f"⚠️ RabbitMQ no listo. Reintentando en 5s... ({e})", flush=True)
            time.sleep(5)
    # ------------------------------------------------
            
    channel = connection.channel()

    # Aseguramos que el Exchange exista
    channel.exchange_declare(exchange='erp_events', exchange_type='topic', durable=True)
    
    # Declaramos una cola exclusiva para este worker
    result = channel.queue_declare(queue='inventory_stock_updates', durable=True)
    queue_name = result.method.queue
    
    # Nos suscribimos a los eventos que nos importan
    channel.queue_bind(exchange='erp_events', queue=queue_name, routing_key='invoice.paid')
    channel.queue_bind(exchange='erp_events', queue=queue_name, routing_key='invoice.voided')
    
    # No tomar más de 1 mensaje a la vez para balancear carga
    channel.basic_qos(prefetch_count=1)
    
    # Configurar el consumidor
    channel.basic_consume(queue=queue_name, on_message_callback=callback)
    
    print("🎧 [Inventory Worker] Escuchando eventos de ventas y anulaciones...", flush=True)
    channel.start_consuming()
    
if __name__ == "__main__":
    try:
        start_worker()
    except KeyboardInterrupt:
        print("🛑 Worker detenido manualmente.")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)