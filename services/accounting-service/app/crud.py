from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, case
from . import models, schemas
import httpx

AUTH_SERVICE_URL = "http://auth-service:8000"

async def get_tenant_data(token: str):
    """Consulta al Auth-Service para obtener Nombre y RIF de la empresa"""
    async with httpx.AsyncClient() as client:
        try:
            # Asumimos que existe este endpoint en Auth (o lo crearemos)
            resp = await client.get(f"{AUTH_SERVICE_URL}/tenant/me", headers={"Authorization": f"Bearer {token}"})
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            print(f"Error contactando Auth: {e}")
            return None

async def create_transaction(db: AsyncSession, transaction: schemas.TransactionCreate, tenant_id: int):
    db_trans = models.Transaction(
        **transaction.model_dump(),
        tenant_id=tenant_id
    )
    db.add(db_trans)
    await db.commit()
    await db.refresh(db_trans)
    return db_trans

async def get_transactions(db: AsyncSession, tenant_id: int):
    query = select(models.Transaction).filter(models.Transaction.tenant_id == tenant_id).order_by(models.Transaction.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

async def get_balance(db: AsyncSession, tenant_id: int):
    # Sumar Ingresos
    q_income = select(func.sum(models.Transaction.amount)).filter(
        models.Transaction.tenant_id == tenant_id,
        models.Transaction.transaction_type == "INCOME"
    )
    res_income = await db.execute(q_income)
    total_income = res_income.scalar() or 0
    
    # Sumar Egresos
    q_expense = select(func.sum(models.Transaction.amount)).filter(
        models.Transaction.tenant_id == tenant_id,
        models.Transaction.transaction_type == "EXPENSE"
    )
    res_expense = await db.execute(q_expense)
    total_expense = res_expense.scalar() or 0
    
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": total_income - total_expense
    }
    
async def get_account_balances(db: AsyncSession, tenant_id: int, start_date: date, end_date: date):
    """
    Calcula el saldo de todas las cuentas para el rango de fechas.
    Retorna un diccionario {account_id: balance}
    """
    # Movimientos del periodo
    query = (
        select(
            models.LedgerLine.account_id,
            func.sum(models.LedgerLine.debit).label('total_debit'),
            func.sum(models.LedgerLine.credit).label('total_credit')
        )
        .join(models.LedgerEntry)
        .filter(
            models.LedgerEntry.tenant_id == tenant_id,
            models.LedgerEntry.transaction_date >= start_date,
            models.LedgerEntry.transaction_date <= end_date
        )
        .group_by(models.LedgerLine.account_id)
    )
    
    result = await db.execute(query)
    movements = result.all()
    
    # Obtiene todas las cuentas apra saber su naturaleza
    accounts_query = select(models.Account).filter(models.Account.tenant_id == tenant_id)
    accounts_res = await db.execute(accounts_query)
    accounts = accounts_res.scalars().all()
    
    # Mapa de cuentas y saldo inicial
    account_map = {acc.id: acc for acc in accounts}
    balances = {acc.id: Decimal(0) for acc in accounts}
    
    # Calcular saldo neto según naturaleza
    for row in movements:
        acc = account_map.get(row.account_id)
        if not acc:
            continue
        
        debit = row.total_debit or Decimal(0)
        credit = row.total_credit or Decimal(0)
        
        # Activos y Gastos: Aumentan por el Debe
        if acc.account_type in ('ASSET', 'EXPENSE'):
            net_movement = debit - credit
        # Pasivos, Patrimonio e Ingresos: Aumenta por el Haber
        else:
            net_movement = credit - debit
        
        balances[row.account_id] = net_movement
        
    # Roll-up
    # Ordena por nivel descendente (4 -> 3 -> 2 -> 1) para subir los saldos
    sorted_accounts = sorted(accounts, key=lambda x: x.level, reverse=True)
    
    final_report = []
    
    # Primero calcula los saldos de los padres
    for acc in sorted_accounts:
        if acc.parent_id:
            balances[acc.parent_id] += balances[acc.id]
    
    # Construye la lista final
    for acc in sorted(accounts, key=lambda x: x.code):
        if balances[acc.id] != 0: # Ocultar cuentas en cero
            final_report.append({
                "code": acc.code,
                "name": acc.name,
                "level": acc.level,
                "type": acc.account_type,
                "balance": balances[acc.id]
            })
            
    return final_report

# --- LÓGICA CORE DE REPORTES ---

async def get_account_balances_at_date(db: AsyncSession, tenant_id: int, cut_off_date: date):
    """
    Calcula SALDOS ACUMULADOS (Balance Sheet) hasta una fecha de corte.
    Suma todo el historial <= cut_off_date.
    """
    query = (
        select(
            models.LedgerLine.account_id,
            func.sum(models.LedgerLine.debit).label('total_debit'),
            func.sum(models.LedgerLine.credit).label('total_credit')
        )
        .join(models.LedgerEntry)
        .filter(
            models.LedgerEntry.tenant_id == tenant_id,
            models.LedgerEntry.transaction_date <= cut_off_date # <= Fecha Corte
        )
        .group_by(models.LedgerLine.account_id)
    )
    return await _process_balances(db, tenant_id, query)

async def get_period_movements(db: AsyncSession, tenant_id: int, start_date: date, end_date: date):
    """
    Calcula MOVIMIENTOS DEL PERIODO (Income Statement / Flujo Efectivo).
    Solo suma lo que pasó entre start y end.
    """
    query = (
        select(
            models.LedgerLine.account_id,
            func.sum(models.LedgerLine.debit).label('total_debit'),
            func.sum(models.LedgerLine.credit).label('total_credit')
        )
        .join(models.LedgerEntry)
        .filter(
            models.LedgerEntry.tenant_id == tenant_id,
            models.LedgerEntry.transaction_date >= start_date,
            models.LedgerEntry.transaction_date <= end_date
        )
        .group_by(models.LedgerLine.account_id)
    )
    return await _process_balances(db, tenant_id, query)

async def _process_balances(db: AsyncSession, tenant_id: int, query):
    """Helper interno para procesar débitos/créditos y jerarquía"""
    # 1. Ejecutar Query de Movimientos
    result = await db.execute(query)
    movements = result.all()
    
    # 2. Traer Plan de Cuentas
    accounts_res = await db.execute(select(models.Account).filter(models.Account.tenant_id == tenant_id))
    accounts = accounts_res.scalars().all()
    
    account_map = {acc.id: acc for acc in accounts}
    balances = {acc.id: Decimal(0) for acc in accounts}
    
    # 3. Calcular Netos
    for row in movements:
        acc = account_map.get(row.account_id)
        if not acc: continue
            
        debit = row.total_debit or Decimal(0)
        credit = row.total_credit or Decimal(0)
        
        # Activos (1), Gastos (6), Costos (5): Aumentan por Debe
        if acc.account_type in ['ASSET', 'EXPENSE'] or acc.code.startswith(('1', '5', '6')):
            balances[row.account_id] = debit - credit
        else: # Pasivo (2), Patrimonio (3), Ingresos (4): Aumentan por Haber
            balances[row.account_id] = credit - debit

    # 4. Roll-up Jerárquico (Hijos suman a Padres)
    sorted_accounts = sorted(accounts, key=lambda x: x.level, reverse=True)
    for acc in sorted_accounts:
        if acc.parent_id and acc.parent_id in balances:
            balances[acc.parent_id] += balances[acc.id]
            
    # 5. Formatear Salida
    report_data = []
    for acc in sorted(accounts, key=lambda x: x.code):
        if balances[acc.id] != 0:
            report_data.append({
                "id": acc.id,
                "code": acc.code,
                "name": acc.name,
                "level": acc.level,
                "type": acc.account_type,
                "balance": balances[acc.id]
            })
    return report_data