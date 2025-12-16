import asyncio
import json
import os
import aio_pika
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import LedgerEntry, LedgerLine, Account, PayrollAccountingConfig
from decimal import Decimal
from datetime import datetime

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

async def get_account_id_by_code(db, code: str, tenant_id: int):
    result = await db.execute(select(Account).where(Account.code == code, Account.tenant_id == tenant_id))
    account = result.scalars().first() 
    return account.id if account else None

async def get_payroll_config(db, tenant_id: int):
    """Obtiene la asignación de contabilidad de nómina para el inquilino"""
    result = await db.execute(select(PayrollAccountingConfig).where(PayrollAccountingConfig.tenant_id == tenant_id))
    return result.scalars().first()

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
    

async def process_payroll_calculated(data: dict):
    """
    Gestiona el evento 'payroll.calculated' del servicio RRHH. 
    Genera un asiento contable basado en el devengo de VEN-NIF.
    """
    payroll_id = data.get("id")
    tenant_id = data.get("tenant_id", 1)
    period_start = data.get("period_start")
    period_end = data.get("period_end")
    
    print(f" [x] 👷 Procesando nómina #{payroll_id} ({period_start} a {period_end})...", flush=True)

    db = AsyncSessionLocal()
    try:
        # Obtiene Configuración
        config = await get_payroll_config(db, tenant_id)
        if not config:
            print(f" [!] ❌ Falta la configuración de contabilidad de nómina para el inquilino {tenant_id}.", flush=True)
            return
        
        # Extrae los Datos
        # Los importes deben ser Decimal
        total_earnings = Decimal(str(data.get("total_earnings", 0)))    # Sueldo Bruto
        
        # Deducciones
        ivss_employee = Decimal(str(data.get("ivss_employee", 0)))
        faov_employee = Decimal(str(data.get("faov_employee", 0)))
        islr_retention = Decimal(str(data.get("islr_retention", 0)))
        
        # Contribuciones del empleador
        ivss_employer = Decimal(str(data.get("ivss_employer", 0)))
        faov_employer = Decimal(str(data.get("faov_employer", 0)))
        
        # Pago Neto
        net_pay = Decimal(str(data.get("net_pay", 0)))
        
        # Crea encabezado de entrada
        description = f"Acumulación de nómina {period_start}/{period_end}"
        entry = LedgerEntry(
            tenant_id=tenant_id,
            transaction_date=datetime.now().date(),
            description=description,
            reference=f"PAYROLL-{payroll_id}",
            total_amount=total_earnings + ivss_employer + faov_employer # Total Debits
        )
        db.add(entry)
        await db.flush()
        
        lines = []
        
        # --- DÉBITOS (GASTOS) ---
        
        # Gastos de Salarios (Brutos)
        if total_earnings > 0 and config.expense_salaries_id:
            lines.append(LedgerLine(entry_id=entry.id, account_id=config.expense_salaries_id, debit=total_earnings, credit=0))
        
        # Gastos de contribuciones del empleador
        if ivss_employer > 0 and config.expense_ivss_employer_id:
            lines.append(LedgerLine(entry_id=entry.id, account_id=config.expense_ivss_employer_id, debit=ivss_employer, credit=0))
            
        if faov_employer > 0 and config.expense_faov_employer_id:
            lines.append(LedgerLine(entry_id=entry.id, account_id=config.expense_faov_employer_id, debit=faov_employer, credit=0))
            
        # --- CRÉDITOS (PASIVOS) ---
        
        # Salarios netos por pagar
        if net_pay > 0 and config.liability_salaries_payable_id:
            lines.append(LedgerLine(entry_id=entry.id, account_id=config.liability_salaries_payable_id, debit=0, credit=net_pay))

        # Impuestos/Contribuciones a pagar (Pasivo = Retención del empleado + Contribución del empleador)
        total_ivss_liability = ivss_employee + ivss_employer
        if total_ivss_liability > 0 and config.liability_ivss_payable_id:
            lines.append(LedgerLine(entry_id=entry.id, account_id=config.liability_ivss_payable_id, debit=0, credit=total_ivss_liability))

        total_faov_liability = faov_employee + faov_employer
        if total_faov_liability > 0 and config.liability_faov_payable_id:
            lines.append(LedgerLine(entry_id=entry.id, account_id=config.liability_faov_payable_id, debit=0, credit=total_faov_liability))
            
        if islr_retention > 0 and config.liability_islr_payable_id:
            lines.append(LedgerLine(entry_id=entry.id, account_id=config.liability_islr_payable_id, debit=0, credit=islr_retention))
            
        # Guarda líneas en masa
        if lines:
            db.add_all(lines)
            await db.commit()
            print(f" [v] ✅ Entrada de diario de nómina #{entry.id} creada correctamente.", flush=True)
        else:
            print(" [!] ⚠️ No se generaron líneas contables. Verifique las cantidades de datos.", flush=True)
            await db.rollback()
        
    except Exception as e:
        print(f" [!] ❌ Error al procesar la nómina: {e}", flush=True)
        await db.rollback()
    finally:
        await db.close()

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
        await queue.bind(exchange, routing_key="payroll.calculated")
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    if message.routing_key == "invoice.created":
                        await process_invoice_created(data)
                    elif message.routing_key == "invoice.paid":
                        await process_payment(data)
                    elif message.routing_key == "payroll.calculated":
                        await process_payroll_calculated(data)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt: pass