import pika
import json
import time
import os
import sys

# Para que Python encuentre los módulos hermanos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.adapters.compliance_ve import VEAdapter

# Configuración
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F")
QUEUE_NAME = "invoice_events"

def get_adapter(country_code="VE"):
    # Cambiar en el futuro para que se elija dinamicamente basado en el pais del cliente
    if country_code == "VE":
        return VEAdapter()
    return VEAdapter() # Default

def callback(ch, method, properties, body):
    """Esta función se ejecuta cada vez que llega un mensaje."""
    print(f"[Compliance] Mensaje recibido!")
    
    try:
        data = json.loads(body)
        print(f"    Datos: {data}")
        
        # Selecciona el adaptador
        adapter = get_adapter("VE")
        
        # Procesa el cumplimiento fiscal
        result = adapter.process_invoice(data)
        
        print(f"✅ [Compliance] Éxito: {result}")
        
        # Llamar de vuelta a Finance-Service para lograr robustez
        
    except Exception as e:
        print(f"❌ [Compliance] Error procesando: {e}")
    
    # Confirmar a RabbitMQ que el mensaje se procesó (ACK)
    ch.basic_ack(delivery_tag=method.delivery_tag)
    
def start_worker():
    print("⏳ [Compliance] Conectando a RabbitMQ")
    connection = None
    
    # Lógica de reintento
    while True:
        try:
            parameters = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(parameters)
            break
        except pika.exceptions.AMQPConnectionError:
            print("     Reintentando conexión en 5s...")
            time.sleep(5)
            
    channel = connection.channel()
    
    # Aseguramos que la cola existe
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    
    # Asegura que Rabbit solo de 1 mensaje a la vez
    channel.basic_qos(prefetch_count=1)
    
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
    
    print("🎧 [Compliance] Esperando facturas.")
    channel.start_consuming()
    
if __name__ == "__main__":
    start_worker()