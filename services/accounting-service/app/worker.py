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

async def process_invoice_issued(data: dict):
    """Crea el asiento contable de una venta"""
    print(f"Procesando Factura #{data.get('id')} - Monto: {data.get('total_amount')}")
    
    db = AsyncSessionLocal()
    try:
        tenant_id = data.get("tenant_id", 1)
        amount = Decimal(str(data.get("total_amount")))
        
        # 1. Buscar Cuentas en el PUC (Códigos Estándar VE)
        # 1.01.03.001 = Cuentas por Cobrar Clientes Nacionales
        ar_account_id = await get_account_id_by_code(db, "1.01.03.001", tenant_id)
        
        # 4.01.01 = Ventas Brutas
        sales_account_id = await get_account_id_by_code(db, "4.01.01", tenant_id)
        
        if not ar_account_id or not sales_account_id:
            print("Error: No se encontraron las cuentas contables (1.01.03.001 o 4.01.01). ¿Corriste el seed?")
            return

        # 2. Crear Cabecera del Asiento
        entry = LedgerEntry(
            tenant_id=tenant_id,
            transaction_date=datetime.now().date(),
            description=f"Venta Factura #{data.get('id')}",
            reference=f"INV-{data.get('id')}",
            total_amount=amount
        )
        db.add(entry)
        await db.flush() # Para obtener ID del asiento

        # 3. Crear Líneas (Partida Doble)
        
        # DÉBITO: Cuentas por Cobrar (Entra derecho de cobro)
        line_debit = LedgerLine(
            entry_id=entry.id,
            account_id=ar_account_id,
            debit=amount,
            credit=0
        )
        
        # CRÉDITO: Ingresos por Ventas (Sale el servicio/bien -> Ingreso)
        line_credit = LedgerLine(
            entry_id=entry.id,
            account_id=sales_account_id,
            debit=0,
            credit=amount
        )
        
        db.add(line_debit)
        db.add(line_credit)
        
        await db.commit()
        print(f"Asiento Contable ID {entry.id} creado exitosamente.")
        
    except Exception as e:
        print(f"Error procesando contabilidad: {e}")
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