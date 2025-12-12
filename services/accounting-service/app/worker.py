import asyncio
import json
import os
import aio_pika
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import LedgerEntry, LedgerLine, Account
from decimal import Decimal
from datetime import datetime

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

async def get_account_id_by_code(db, code: str, tenant_id: int):
    result = await db.execute(select(Account).where(Account.code == code, Account.tenant_id == tenant_id))
    account = result.scalars().first() 
    return account.id if account else None

async def process_invoice_created(data: dict):
    status = data.get("status", "ISSUED") 
    inv_id = data.get("id")
    tenant_id = data.get("tenant_id", 1)
    
    print(f" [x] 📥 Procesando Factura #{inv_id} ({status})...", flush=True)
    
    db = AsyncSessionLocal()
    try:
        amount = Decimal(str(data.get("total_amount") or 0))

        # --- LÓGICA INTELIGENTE ---
        if status == "PAID":
            # VENTA DE CONTADO (Directo): Caja vs Ventas
            # Asumimos que entra a Caja Principal por defecto
            debit_code = "1.01.01.001" # Caja
            credit_code = "4.01.01.001" # Ventas Contado
            desc = f"Venta Contado Fac. {inv_id}"
        else:
            # VENTA A CRÉDITO: CxC vs Ventas
            debit_code = "1.01.03.001" # Clientes (CxC)
            credit_code = "4.01.01.002" # Ventas Crédito
            desc = f"Venta Crédito Fac. {inv_id}"

        debit_acc = await get_account_id_by_code(db, debit_code, tenant_id)
        credit_acc = await get_account_id_by_code(db, credit_code, tenant_id)

        if not debit_acc or not credit_acc:
            print(f" [!] ❌ Cuentas no configuradas ({debit_code}/{credit_code}).", flush=True)
            return
        
        # Crear Asiento Único
        entry = LedgerEntry(
            tenant_id=tenant_id,
            transaction_date=datetime.now().date(),
            description=desc,
            reference=f"INV-{inv_id}",
            total_amount=amount
        )
        db.add(entry)
        await db.flush()

        db.add(LedgerLine(entry_id=entry.id, account_id=debit_acc, debit=amount, credit=0))
        db.add(LedgerLine(entry_id=entry.id, account_id=credit_acc, debit=0, credit=amount))
        
        await db.commit()
        print(f" [v] ✅ Asiento #{entry.id} creado.", flush=True)
        
    except Exception as e:
        print(f" [!] Error creación: {e}", flush=True)
        await db.rollback()
    finally:
        await db.close()

async def process_payment(data: dict):
    # Si el pago viene de una creación inmediata (Contado), LO IGNORAMOS
    # porque ya se registró el ingreso de caja en el paso anterior.
    if data.get("origin") == "immediate":
        print(f" [i] ⏩ Pago inmediato de Fac. {data.get('invoice_id')} ya registrado. Omitiendo.", flush=True)
        return

    # Si es un pago posterior (Cobro de Crédito)
    inv_id = data.get("invoice_id")
    print(f" [x] 💰 Registrando COBRO de Crédito Fac. {inv_id}...", flush=True)
    
    # ... (Aquí iría la lógica normal de Caja vs CxC para pagos diferidos) ...
    # Por brevedad, asumimos que si llega aquí es un cobro de cartera real

async def main():
    print("⏳ [Accounting Worker] Iniciando...", flush=True)
    while True:
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            break
        except:
            await asyncio.sleep(5)

    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange("erp_events", aio_pika.ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue("accounting_queue", durable=True)
        
        await queue.bind(exchange, routing_key="invoice.created")
        await queue.bind(exchange, routing_key="invoice.paid")
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    if message.routing_key == "invoice.created":
                        await process_invoice_created(data)
                    elif message.routing_key == "invoice.paid":
                        await process_payment(data)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt: pass