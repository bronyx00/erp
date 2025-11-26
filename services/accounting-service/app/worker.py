import pika
import json
import os
import time
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# Evita errores de path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.models import Transaction
from app.database import DATABASE_URL

# Configuración
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F")
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def register_income_from_invoice(data):
    db = SessionLocal()
    try:
        tenant_id = data.get("tenant_id")
        if not tenant_id:
            print("⚠️ Evento sin tenant_id, ignorando.")
            return
        
        # Calcular total pagado sumando los items 
        amount = data.get("total_amount", 0)
        invoice_id = data.get("invoice_id")
        
        trans = Transaction(
            tenant_id=tenant_id,
            transaction_type="INCOME",
            category="Ventas",
            amount=amount,
            currency="USD",
            description=f"Cobro Factura #${invoice_id}",
            reference_id=str(invoice_id)
        )
        db.add(trans)
        db.commit()
        print(f"💰 Ingreso registrado: ${amount} (Factura #{invoice_id})")
        
    except Exception as e:
        print(f"❌ Error registrando ingreso: {e}")
        db.rollback()
    finally:
        db.close()
        
def register_transaction(data, trans_type):
    db = SessionLocal()
    try:
        tenant_id = data.get("tenant_id")
        if not tenant_id: return
        
        # Adaptamos los campos según el evento
        amount = data.get("amount") or data.get("total_amount", 0)
        category = data.get("category", "Ventas")
        desc = data.get("description", "")
        ref_id = data.get("reference_id") or str(data.get("invoice_id", ""))
        
        trans = Transaction(
            tenant_id=tenant_id,
            transaction_type=trans_type, # INCOME o EXPENSE
            category=category,
            amount=amount,
            currency="USD",
            description=desc,
            reference_id=ref_id
        )
        db.add(trans)
        db.commit()
        print(f"📝 {trans_type} registrado: ${amount} - {category}")
    
    except Exception as e:
        print(f"❌ Error DB: {e}")
        db.rollback()
    finally:
        db.close()
    
def callback(ch, method, properties, body):
    print(f"📥 [Accounting] Evento: {method.routing_key}")
    try:
        message = json.loads(body)
        # A veces el payload viene directo o dentro de 'data'
        payload = message if "tenant_id" in message else message.get("data", {})
        
        if method.routing_key == "invoice.paid":
            # Venta -> Ingreso
            register_transaction(payload, "INCOME")
        elif method.routing_key == "payroll.paid":
            # Nómina -> Gasto
            register_transaction(payload, "EXPENSE")
            
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
def start_worker():
    print("⏳ [Accounting Worker] Conectando...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange='erp_events', exchange_type='topic', durable=True)
    
    result = channel.queue_declare(queue='accounting_ledger', durable=True)
    queue_name = result.method.queue
    
    channel.queue_bind(exchange='erp_events', queue=queue_name, routing_key='invoice.paid')
    channel.queue_bind(exchange='erp-events', queue=queue_name, routing_key='payroll.paid')
    
    channel.basic_consume(queue=queue_name, on_message_callback=callback)
    print("🎧 [Accounting Worker] Escuchando dinero...")
    channel.start_consuming()

if __name__ == "__main__":
    start_worker()