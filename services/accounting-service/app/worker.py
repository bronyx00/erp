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
    """Busca el ID de una cuenta por su código PUC"""
    result = await db.execute(select(Account).where(Account.code == code, Account.tenant_id == tenant_id))
    account = result.scalar_one_or_none()
    return account.id if account else None

async def process_invoice_created(data: dict):
    status = data.get("status", "ISSUED") 
    inv_id = data.get("id")
    
    print(f" [x] Procesando Factura #{inv_id} - Estado: {status}")
    
    db = AsyncSessionLocal()
    try:
        tenant_id = data.get("tenant_id", 1)
        
        raw_amount = data.get("total_amount")
        if raw_amount is None:
            print(" [!] Error: Factura sin monto. Se omite.")
            return
        amount = Decimal(str(raw_amount))

        # 1. Definir Cuenta DEBE (A donde entra el dinero)
        debit_account_code = "1.01.03.001" # Por defecto: CxC (Crédito)
        
        if status == "PAID":
            # Si el POS la marca pagada, va a CAJA
            debit_account_code = "1.01.01.001" 
            print("   -> Venta de Contado (Caja)")
        else:
            # Si es ISSUED, va a CUENTAS POR COBRAR
            print("   -> Venta a Crédito (CxC)")

        # 2. Definir Cuenta HABER (Ventas)
        credit_account_code = "4.01.01" # Ventas Brutas

        # 3. Buscar IDs
        debit_acc_id = await get_account_id_by_code(db, debit_account_code, tenant_id)
        credit_acc_id = await get_account_id_by_code(db, credit_account_code, tenant_id)

        if not debit_acc_id or not credit_acc_id:
            print(f" [!] Error: No se encontraron las cuentas {debit_account_code} o {credit_account_code} en el PUC.")
            return
        
        str_status = ''
        if status == 'PAID':
            str_status = 'CONTADO'
        elif status == 'PARTIALLY_PAID':
            str_status = 'Parcialmente pagado'
        elif status == 'ISSUED':
            str_status = 'CREDITO'
        else:
            str_status = 'CANCELADA'

        # 4. Crear Asiento
        entry = LedgerEntry(
            tenant_id=tenant_id,
            transaction_date=datetime.now().date(),
            description=f"Venta Factura #{inv_id} ({str_status})",
            reference=f"INV-{inv_id}",
            total_amount=amount
        )
        db.add(entry)
        await db.flush()

        # 5. Líneas
        # Debe
        db.add(LedgerLine(entry_id=entry.id, account_id=debit_acc_id, debit=amount, credit=0))
        # Haber
        db.add(LedgerLine(entry_id=entry.id, account_id=credit_acc_id, debit=0, credit=amount))
        
        await db.commit()
        print(f" [v] Asiento ID {entry.id} creado exitosamente.")
        
    except Exception as e:
        print(f" [!] Error procesando contabilidad: {e}")
        await db.rollback()
    finally:
        await db.close()

async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        
        # Declarar Exchange y Queue
        exchange = await channel.declare_exchange(
            "erp_events", 
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        queue = await channel.declare_queue("accounting_queue", durable=True)
        
        # Bind: Escuchar eventos de facturas
        await queue.bind(exchange, routing_key="invoice.created")
        
        print("Accounting Worker esperando eventos...")
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    routing_key = message.routing_key
                    
                    if routing_key == "invoice.created":
                        await process_invoice_issued(data)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Worker detenido.")