from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
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