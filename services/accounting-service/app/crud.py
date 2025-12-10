from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, case
from . import models, schemas

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