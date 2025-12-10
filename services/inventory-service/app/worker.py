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
    if country_code == "VE":
        return VEAdapter()
    return VEAdapter() # Default

def callback(ch, method, properties, body):
    """Esta función se ejecuta cada vez que llega un mensaje."""
    print(f"[Compliance] Mensaje recibido!", flush=True)
    
    try:
        data = json.loads(body)
        
        # Selecciona el adaptador
        adapter = get_adapter("VE")
        
        # Procesa el cumplimiento fiscal
        result = adapter.process_invoice(data)
        
        print(f"✅ [Compliance] Éxito: {result}", flush=True)
        
    except Exception as e:
        print(f"❌ [Compliance] Error procesando: {e}", flush=True)
    
    # Confirmar a RabbitMQ que el mensaje se procesó (ACK)
    ch.basic_ack(delivery_tag=method.delivery_tag)
    
def start_worker():
    print("⏳ [Compliance] Iniciando...", flush=True)
    connection = None
    
    # --- BUCLE DE ESPERA INTELIGENTE ---
    while True:
        try:
            parameters = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(parameters)
            print("✅ [Compliance] Conectado a RabbitMQ", flush=True)
            break
        except (pika.exceptions.AMQPConnectionError, OSError) as e:
            # Captura errores de conexión y de DNS/Socket
            print(f"⚠️ RabbitMQ no listo. Reintentando en 5s... ({e})", flush=True)
            time.sleep(5)
    # -----------------------------------
            
    channel = connection.channel()

    channel.exchange_declare(exchange='erp_events', exchange_type='topic', durable=True)

    # Declarar la cola
    queue_name = "invoice_events"
    channel.queue_declare(queue=queue_name, durable=True)

    # Esto dice: "Mándame a esta cola todo lo que tenga la etiqueta 'invoice.created'"
    channel.queue_bind(exchange='erp_events', queue=queue_name, routing_key='invoice.created')

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    print("🎧 [Compliance] Escuchando eventos 'invoice.created'...", flush=True)
    channel.start_consuming()
    
if __name__ == "__main__":
    start_worker()