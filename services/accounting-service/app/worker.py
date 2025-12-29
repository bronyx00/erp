import asyncio
import json
import os
import sys
import aio_pika
from decimal import Decimal
from datetime import date, datetime
from app import database, models
from sqlalchemy.future import select
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# Ajuste de path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import AsyncSessionLocal
from app.models import LedgerEntry, LedgerLine, Account, PayrollAccountingConfig

RABBITMQ_URL = os.getenv("RABBITMQ_URL")

@retry(stop=stop_after_attempt(15), wait=wait_fixed(5), retry=retry_if_exception_type(Exception))
async def get_rabbitmq_connection():
    print(f"⏳ [Accounting] Conectando a RabbitMQ...", flush=True)
    return await aio_pika.connect_robust(RABBITMQ_URL)

async def get_account_id_by_code(db, code: str, tenant_id: int):
    result = await db.execute(select(Account).where(Account.code == code, Account.tenant_id == tenant_id))
    account = result.scalars().first() 
    return account.id if account else None

async def get_payroll_config(db, tenant_id: int):
    """Obtiene la asignación de contabilidad de nómina para el inquilino"""
    result = await db.execute(select(PayrollAccountingConfig).where(PayrollAccountingConfig.tenant_id == tenant_id))
    return result.scalars().first()

async def process_cash_close(data: dict):
    """
    Genera un asiento contable por todo el turno/dia.
    """
    summary = data.get("summary", {})
    tenant_id = data.get("tenant_id")
    close_id = data.get("cash_close_id")
    
    print(f" [x] 💰 Procesando Cierre de Caja #{close_id}...", flush=True)
    
    db = AsyncSessionLocal()
    try:
        # Convierte a Decimal
        total_sales_base = Decimal(str(summary.get("total_sales_usd", 0)))  # Venta neta (sin IVA)
        total_tax = Decimal(str(summary.get("total_tax_usd", 0)))           # IVA
        
        # Efectivo (USD Real + VES convertido a USD)
        cash_usd_real = Decimal(str(summary.get("collected_cash_usd", 0)))
        cash_ves_equiv = Decimal(str(summary.get("collected_cash_ves_equiv", 0)))
        total_cash_debit = cash_usd_real + cash_ves_equiv

        # Banco (USD Real + VES convertido a USD)
        bank_usd_real = Decimal(str(summary.get("collected_bank_usd", 0)))
        bank_ves_equiv = Decimal(str(summary.get("collected_bank_ves_equiv", 0)))
        total_bank_debit = bank_usd_real + bank_ves_equiv
        
        sales_on_credit = Decimal(str(summary.get("sales_on_credit_usd", 0)))
        
        # Validación básica de balance
        total_debits = total_cash_debit + total_bank_debit + sales_on_credit
        total_credits = total_sales_base + total_tax
        
        # Crear Encabezado
        entry = LedgerEntry(
            tenant_id=tenant_id,
            transaction_date=datetime.now().date(),
            description=f"Cierre de Caja Global #{close_id}",
            reference=f"CLOSE-{close_id}",
            total_amount=total_debits 
        )
        db.add(entry)
        await db.flush()
        
        # --- OBTENER CUENTAS ---
        # 1. ACTIVO
        acc_cash = await get_account_id_by_code(db, "1.01.01.001", tenant_id) # Caja Principal
        acc_bank = await get_account_id_by_code(db, "1.01.01.003", tenant_id) # Banco Nacional
        acc_ar   = await get_account_id_by_code(db, "1.01.03.001", tenant_id) # Cuentas por Cobrar Clientes
        
        # 2. INGRESOS Y PASIVOS
        acc_sales = await get_account_id_by_code(db, "4.01.01.001", tenant_id) # Ventas Mercancía
        acc_vat   = await get_account_id_by_code(db, "2.01.02.001", tenant_id) # Débito Fiscal IVA
        
        lines = []
        
        # --- GENERAR LINEAS (DEBE) ---
        if total_cash_debit > 0 and acc_cash:
            lines.append(LedgerLine(entry_id=entry.id, account_id=acc_cash, debit=total_cash_debit, credit=0))
            
        if total_bank_debit > 0 and acc_bank:
            lines.append(LedgerLine(entry_id=entry.id, account_id=acc_bank, debit=total_bank_debit, credit=0))
            
        if sales_on_credit > 0 and acc_ar:
            lines.append(LedgerLine(entry_id=entry.id, account_id=acc_ar, debit=sales_on_credit, credit=0))

        # --- GENERAR LINEAS (HABER) ---
        if total_sales_base > 0 and acc_sales:
            lines.append(LedgerLine(entry_id=entry.id, account_id=acc_sales, debit=0, credit=total_sales_base))
            
        if total_tax > 0 and acc_vat:
            lines.append(LedgerLine(entry_id=entry.id, account_id=acc_vat, debit=0, credit=total_tax))
            
        if lines:
            db.add_all(lines)
            await db.commit()
            print(f" [v] ✅ Asiento Global de Cierre #{entry.id} creado.", flush=True)
        else:
            print(" [!] ⚠️ Cierre sin movimientos financieros.", flush=True)
            await db.rollback()

    except Exception as e:
        print(f" [!] Error creación Asiento Cierre: {e}", flush=True)
        await db.rollback()
    finally:
        await db.close()
        
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

async def process_payroll_batch_event(payload):
    print(f"📥 [Accounting] Procesando Lote de Nómina")
    
    tenant_id = payload['tenant_id']
    payment_method = payload.get('payment_method', 'BANK_TRANSFER')
    
    target_account_code = payload.get('payment_account_code')
    if not target_account_code:
        target_account_code = "1.01.01.001" if payment_method == "CASH" else "1.01.01.003"
    
    description = payload.get('notes', 'Pago Masivo Nómina')
    tx_date = date.fromisoformat(payload['paid_at'])
    
    # Extraer montos detallados
    total_net_pay = Decimal(str(payload['total_net_pay']))             
    total_expense_salary = Decimal(str(payload['total_expense_salary'])) 
    total_expense_contrib = Decimal(str(payload['total_expense_contrib']))
    
    # Pasivos específicos
    liability_ivss = Decimal(str(payload.get('liability_ivss', 0)))
    liability_faov = Decimal(str(payload.get('liability_faov', 0)))
    liability_other = Decimal(str(payload.get('liability_other', 0))) # ISLR, etc
    
    # El monto total del asiento
    total_transaction_amount = total_net_pay + liability_ivss + liability_faov + liability_other
    
    async with database.AsyncSessionLocal() as db:
        try:
            # A. CUENTA DE PAGO
            bank_acc = (await db.execute(select(models.Account).filter_by(code=target_account_code, tenant_id=tenant_id))).scalars().first()
            if not bank_acc:
                print(f"❌ Cuenta Banco {target_account_code} no existe.")
                return
            
            # B. CUENTAS DE GASTO
            # 6.01.01.001: Sueldos y Salarios
            salary_acc = (await db.execute(select(models.Account).filter_by(code="6.01.01", tenant_id=tenant_id))).scalars().first()
            
            contrib_acc = salary_acc
            
            # C. CUENTAS DE PASIVOS
            
            # 2.01.03.003: SSO / IVSS por Pagar
            ivss_acc = (await db.execute(select(models.Account).filter_by(code="2.01.03.003", tenant_id=tenant_id))).scalars().first()
            
            # 2.01.03.004: FAOV por Pagar
            faov_acc = (await db.execute(select(models.Account).filter_by(code="2.01.03.004", tenant_id=tenant_id))).scalars().first()
            
            # 2.01.03.001: Sueldos por Pagar (Para el resto/ISLR si no hay cuenta especifica)
            other_liability_acc = (await db.execute(select(models.Account).filter_by(code="2.01.03.001", tenant_id=tenant_id))).scalars().first()

            if not salary_acc or not ivss_acc or not faov_acc:
                print("❌ Faltan cuentas del PUC (IVSS o FAOV por pagar).")
                return
            
            # --- 2. CREAR ASIENTO ---
            entry = models.LedgerEntry(
                tenant_id=tenant_id,
                transaction_date=tx_date,
                description=description,
                reference=payload.get('reference', 'NOMINA'),
                total_amount=total_transaction_amount
            )
            db.add(entry)
            await db.flush()
            
            # --- 3. CREAR LÍNEAS DETALLADAS ---
            
            # [DEBE] Gasto Sueldos (Bruto)
            if total_expense_salary > 0:
                db.add(models.LedgerLine(entry_id=entry.id, account_id=salary_acc.id, debit=total_expense_salary, credit=0))
            
            # [DEBE] Gasto Aportes Patronales
            if total_expense_contrib > 0:
                db.add(models.LedgerLine(entry_id=entry.id, account_id=contrib_acc.id, debit=total_expense_contrib, credit=0))
                
            # [HABER] Banco (Salida neta)
            if total_net_pay > 0:
                db.add(models.LedgerLine(entry_id=entry.id, account_id=bank_acc.id, debit=0, credit=total_net_pay))
            
            # [HABER] Pasivo IVSS (Deuda con el Seguro Social)
            if liability_ivss > 0:
                db.add(models.LedgerLine(entry_id=entry.id, account_id=ivss_acc.id, debit=0, credit=liability_ivss))

            # [HABER] Pasivo FAOV (Deuda con Banavih)
            if liability_faov > 0:
                db.add(models.LedgerLine(entry_id=entry.id, account_id=faov_acc.id, debit=0, credit=liability_faov))

            # [HABER] Otros Pasivos (ISLR, etc)
            if liability_other > 0:
                db.add(models.LedgerLine(entry_id=entry.id, account_id=other_liability_acc.id, debit=0, credit=liability_other))
                
            await db.commit()
            print(f"✅ Asiento de Nómina ID {entry.id} creado con cuentas PUC Venezuela.")
            
        except Exception as e:
            print(f"❌ Error en asiento contable: {e}")
            await db.rollback()
            

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            routing_key = message.routing_key
            print(f"📥 [Accounting] Evento recibido: {routing_key}", flush=True)

            if routing_key == "payroll.calculated":
                await process_payroll_calculated(data)
            elif routing_key == "payroll.batch_paid":
                await process_payroll_batch_event(data)
            elif routing_key == "finance.cash_close_created":
                await process_cash_close(data)
                
        except Exception as e:
            print(f"❌ Error procesando mensaje: {e}", flush=True)

async def main():
    connection = await get_rabbitmq_connection()
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange("erp_events", aio_pika.ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue("accounting_queue", durable=True)
        
        await queue.bind(exchange, routing_key="finance.cash_close_created")
        await queue.bind(exchange, routing_key="payroll.calculated")
        await queue.bind(exchange, routing_key="payroll.batch_paid")
        
        print("🎧 [Accounting] Escuchando eventos financieros...", flush=True)
        await queue.consume(process_message)
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass