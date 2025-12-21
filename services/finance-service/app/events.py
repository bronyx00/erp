import pika
import json
import os
import logging

logger = logging.getLogger("finance-service")

def publish_event(routing_key: str, data: dict):
    """Publica un evento en el bus de mensajes para notificar a otros servicios."""
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