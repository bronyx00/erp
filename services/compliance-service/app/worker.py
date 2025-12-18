import asyncio
import json
import os
import sys
import aio_pika
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.adapters.compliance_ve import VEAdapter

RABBITMQ_URL = os.getenv("RABBITMQ_URL")

@retry(stop=stop_after_attempt(15), wait=wait_fixed(5), retry=retry_if_exception_type(Exception))
async def get_rabbitmq_connection():
    print(f"⏳ [Compliance] Conectando a RabbitMQ...", flush=True)
    return await aio_pika.connect_robust(RABBITMQ_URL)

def get_adapter(country_code="VE"):
    # Cambiar en el futuro para que se elija dinamicamente basado en el pais del cliente
    if country_code == "VE":
        return VEAdapter()
    return VEAdapter() # Default

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            data = json.loads(message.body)
            print(f"📥 [Compliance] Procesando factura para impuestos...", flush=True)
            
            # Nota: Si el adaptador es síncrono (no usa await), se ejecuta directo.
            # Si consume mucho CPU, idealmente se usaría run_in_executor, pero por ahora está bien así.
            adapter = VEAdapter()
            result = adapter.process_invoice(data)
            
            print(f"✅ [Compliance] Resultado: {result}", flush=True)
        except Exception as e:
            print(f"❌ [Compliance] Error: {e}", flush=True)

async def main():
    connection = await get_rabbitmq_connection()
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange('erp_events', aio_pika.ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue("invoice_events", durable=True)
        
        await queue.bind(exchange, routing_key='invoice.created')
        
        print("🎧 [Compliance] Escuchando eventos fiscales...", flush=True)
        await queue.consume(process_message)
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass