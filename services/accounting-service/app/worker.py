import asyncio
import json
import os
import aio_pika
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import LedgerEntry, LedgerLine, Account
from decimal import Decimal
from datetime import datetime

# URL de conexión
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

async def get_account_id_by_code(db, code: str, tenant_id: int):
    """Busca el ID de una cuenta por su código PUC"""
    result = await db.execute(select(Account).where(Account.code == code, Account.tenant_id == tenant_id))
    
    # --- CORRECCIÓN AQUÍ ---
    # Usamos .first() en lugar de .one_or_none() para tolerar duplicados si la BD está sucia
    account = result.scalars().first() 
    return account.id if account else None

async def process_invoice_created(data: dict):
    """Procesa el evento de factura creada para generar el asiento contable"""
    status = data.get("status", "ISSUED") 
    inv_id = data.get("id")
    tenant_id = data.get("tenant_id", 1)
    
    print(f" [x] 📥 Procesando Factura #{inv_id} (Tenant: {tenant_id}) - Estado: {status}")
    
    db = AsyncSessionLocal()
    try:
        raw_amount = data.get("total_amount") or data.get("amount")
        if raw_amount is None:
            print(" [!] ⚠️ Error: Factura sin monto. Se omite.")
            return
            
        amount = Decimal(str(raw_amount))

        # 1. Definir Cuentas (PUC VENEZUELA)
        if status == "PAID":
            # Contado: Entra a CAJA, Sale de VENTAS
            debit_code = "1.01.01.001" 
            credit_code = "4.01.01.001"
            desc_status = "CONTADO"
        else:
            # Crédito: Entra a CxC CLIENTES, Sale de VENTAS
            debit_code = "1.01.03.001"
            credit_code = "4.01.01.002" 
            desc_status = "CRÉDITO"

        # 2. Buscar IDs en la BD
        debit_acc_id = await get_account_id_by_code(db, debit_code, tenant_id)
        credit_acc_id = await get_account_id_by_code(db, credit_code, tenant_id)

        if not debit_acc_id:
            print(f" [!] ❌ Error: No existe la cuenta DEBITO {debit_code}. ¡Ejecuta el seed!")
            return
        if not credit_acc_id:
            print(f" [!] ❌ Error: No existe la cuenta CREDITO {credit_code}. ¡Ejecuta el seed!")
            return
        
        # 3. Crear Asiento (Cabecera)
        entry = LedgerEntry(
            tenant_id=tenant_id,
            transaction_date=datetime.now().date(),
            description=f"Venta Fac. {data.get('invoice_number', inv_id)} - {desc_status}",
            reference=f"INV-{inv_id}",
            total_amount=amount
        )
        db.add(entry)
        await db.flush()

        # 4. Crear Líneas (Detalle)
        # DEBE
        db.add(LedgerLine(entry_id=entry.id, account_id=debit_acc_id, debit=amount, credit=0))
        # HABER
        db.add(LedgerLine(entry_id=entry.id, account_id=credit_acc_id, debit=0, credit=amount))
        
        await db.commit()
        print(f" [v] ✅ Asiento Contable #{entry.id} registrado exitosamente.")
        
    except Exception as e:
        print(f" [!] 💥 Error procesando contabilidad: {e}")
        await db.rollback()
    finally:
        await db.close()

async def main():
    print("⏳ [Accounting Worker] Conectando a RabbitMQ...")
    # Bucle de reintento simple para conexión inicial
    while True:
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            break
        except Exception:
            print(" [!] RabbitMQ no listo, reintentando en 5s...")
            await asyncio.sleep(5)

    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange("erp_events", aio_pika.ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue("accounting_queue", durable=True)
        
        await queue.bind(exchange, routing_key="invoice.created")
        await queue.bind(exchange, routing_key="invoice.paid")
        
        print("🎧 [Accounting Worker] Esperando eventos...")
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        data = json.loads(message.body.decode())
                        routing_key = message.routing_key
                        
                        if routing_key == "invoice.created":
                            await process_invoice_created(data)
                        elif routing_key == "invoice.paid":
                            print(f" [i] Pago recibido para factura {data.get('invoice_id')}")
                    except Exception as e:
                        print(f" [!] Error en mensaje: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass