import pika
import json
import os
import logging
from decimal import Decimal
from datetime import date, datetime

logger = logging.getLogger("finance-service")

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) # O str(obj) si prefieres exactitud total
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        # Si es un objeto ORM u otro desconocido, intentamos convertirlo a string como último recurso
        return str(obj)

def publish_event(routing_key: str, data: dict):
    """Publica un evento en el bus de mensajes para notificar a otros servicios."""
    try:
        url = os.getenv("RABBITMQ_URL", 'amqp://guest:guest@rabbitmq:5672/%2F')
        connection = pika.BlockingConnection(pika.URLParameters(url))
        channel = connection.channel()
        channel.exchange_declare(exchange='erp_events', exchange_type='topic', durable=True)
        
        message_body = json.dumps(data, cls=CustomJSONEncoder)
        
        channel.basic_publish(
            exchange='erp_events',
            routing_key=routing_key,
            body=message_body,
            properties=pika.BasicProperties(delivery_mode=2, content_type='application/json')
        )
        connection.close()
        logger.info(f"📢 Evento publicado: {routing_key}")
    except Exception as e:
        logger.error(f"❌ Error publicando evento {routing_key}: {e}")