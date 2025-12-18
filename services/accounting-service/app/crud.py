from datetime import date
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text
from . import models, schemas
import httpx
import os

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")

async def get_tenant_data(token: str) -> Optional[Dict[str, Any]]:
    """
    Consulta al microservicio de Auth para obtener detalles de la empresa (Tenant).
    
    Args:
        token (str): Token JWT del usuario actual.

    Returns:
        Optional[Dict[str, Any]]: Datos de la empresa (nombre, rif) o None si falla.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{AUTH_SERVICE_URL}/tenant/me", 
                headers={"Authorization": f"Bearer {token}"}
            )
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            print(f"Error contactando Auth: {e}")
            return None

async def create_transaction(
    db: AsyncSession, 
    transaction: schemas.TransactionCreate, 
    tenant_id: int
) -> models.Transaction:
    """
    Registra una nueva transacción financiera (Ingreso/Egreso) en la base de datos.

    Args:
        db (AsyncSession): Sesión de base de datos.
        transaction (TransactionCreate): Datos validados de la transacción.
        tenant_id (int): ID de la empresa propietaria.

    Returns:
        models.Transaction: La transacción creada con su ID asignado.
    """
    db_trans = models.Transaction(
        **transaction.model_dump(),
        tenant_id=tenant_id
    )
    db.add(db_trans)
    await db.commit()
    await db.refresh(db_trans)
    return db_trans

async def get_transactions(
    db: AsyncSession, 
    tenant_id: int,
    limit: int = 100
) -> List[models.Transaction]:
    """
    Obtiene las últimas transacciones registradas de una empresa.

    Args:
        db (AsyncSession): Sesión de base de datos.
        tenant_id (int): ID de la empresa.
        limit (int): Límite de registros a retornar (Default: 100).

    Returns:
        List[models.Transaction]: Lista de transacciones ordenadas por fecha reciente.
    """
    query = (
        select(models.Transaction)
        .filter(models.Transaction.tenant_id == tenant_id)
        .order_by(models.Transaction.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()

async def get_balance(db: AsyncSession, tenant_id: int) -> dict[str, Decimal]:
    """
    Calcula el balance general simple (Ingresos vs Egresos).
    
    Realiza una agregación SQL para sumar montos por tipo de transacción.

    Args:
        db (AsyncSession): Sesión de base de datos.
        tenant_id (int): ID de la empresa.

    Returns:
        Dict[str, Decimal]: Diccionario con 'total_income', 'total_expense', 'net_profit'.
    """
    # 1. Sumar Ingresos
    q_income = select(func.sum(models.Transaction.amount)).filter(
        models.Transaction.tenant_id == tenant_id,
        models.Transaction.transaction_type == "INCOME"
    )
    
    # 2. Sumar Egresos
    q_expense = select(func.sum(models.Transaction.amount)).filter(
        models.Transaction.tenant_id == tenant_id,
        models.Transaction.transaction_type == "EXPENSE"
    )
    
    # Ejecuta en paralelo
    res_income = await db.execute(q_income)
    res_expense = await db.execute(q_expense)
    
    total_income = res_income.scalar() or Decimal(0)
    total_expense = res_expense.scalar() or Decimal(0)
    
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": total_income - total_expense
    }
    
# --- REPORTE CONTABLE ---
async def get_account_balances(
    db: AsyncSession, 
    tenant_id: int, 
    start_date: date, 
    end_date: date
) -> List[Dict[str, Any]]:
    """
    Genera el Balance de Comprobación usando SQL Recursivo.
    
    Esta función es crítica para el rendimiento. En lugar de procesar miles
    de líneas en Python, usa una CTE (Common Table Expression) en PostgreSQL
    para sumar jerárquicamente los saldos desde las cuentas hijas hasta las padres.

    Args:
        db (AsyncSession): Sesión de base de datos.
        tenant_id (int): ID de la empresa.
        start_date (date): Fecha inicio del periodo.
        end_date (date): Fecha fin del periodo.

    Returns:
        List[Dict]: Lista plana de cuentas con sus saldos calculados y jerarquía.
    """
    
    # Consulta SQL para sumar hijos a padres automáticamente
    sql = text("""
    WITH RECURSIVE account_tree AS (
        -- 1. Caso Base: Cuentas que tienen movimientos directos
        SELECT 
            a.id, a.parent_id, a.code, a.name, a.level, a.account_type,
            COALESCE(SUM(l.debit), 0) as total_debit,
            COALESCE(SUM(l.credit), 0) as total_credit
        FROM accounts a
        LEFT JOIN ledger_lines l ON l.account_id = a.id
        LEFT JOIN ledger_entries e ON l.entry_id = e.id 
             AND e.transaction_date BETWEEN :start AND :end
             AND e.tenant_id = :tenant_id
        WHERE a.tenant_id = :tenant_id
        GROUP BY a.id
        
        UNION ALL
        
        -- 2. Sumar hijos a sus padres
        SELECT 
            p.id, p.parent_id, p.code, p.name, p.level, p.account_type,
            c.total_debit,
            c.total_credit
        FROM accounts p
        JOIN account_tree c ON c.parent_id = p.id
    )
    -- 3. Agrupación final para consolidar sumas recursivas
    SELECT 
        id, code, name, level, account_type,
        SUM(total_debit) as final_debit,
        SUM(total_credit) as final_credit
    FROM account_tree
    GROUP BY id, code, name, level, account_type
    ORDER BY code;
    """)
    
    # Ejecuta la consulta
    result = await db.execute(sql, {
        "tenant_id": tenant_id, 
        "start": start_date, 
        "end": end_date
    })
    
    # Convierte a diccionario
    rows = result.mappings().all()
    
    final_report = []
    
    # Procesa el saldo neto según la naturaleza contable
    for row in rows:
        debit = row['final_debit']
        credit = row['final_credit']

        # Activos y Gastos: Naturaleza Deudora
        if row['account_type'] in ('ASSET', 'EXPENSE'):
            balance = debit - credit
        # Pasivo, Patrimonio e Ingresos: Naturaleza Acreedora
        else:
            balance = credit - debit
            
        # Solo muestra cuentas con movimientos o saldo
        if balance != 0 or debit != 0 or credit != 0:
            final_report.append({
                "code": row['code'],
                "name": row['name'],
                "level": row['level'],
                "type": row['account_type'],
                "debit": debit,
                "credit": credit,
                "balance": balance
            })
            
    return final_report

# --- REPORTES FINANCIEROS OPTIMIZADOS ---

async def get_account_balances_at_date(
    db: AsyncSession, 
    tenant_id: int, 
    cut_off_date: date
) -> List[Dict[str, Any]]:
    """
    Calcula los SALDOS ACUMULADOS (Balance Sheet) hasta una fecha de corte.
    
    Ideal para el Balance General. Suma todo el histórico de movimientos 
    desde el inicio de los tiempos hasta la fecha indicada.
    
    Args:
        db (AsyncSession): Sesión de base de datos.
        tenant_id (int): ID de la empresa.
        cut_off_date (date): Fecha de corte para el reporte.

    Returns:
        List[Dict]: Lista de cuentas con sus saldos acumulados finales.
    """
    # Usamos una fecha muy antigua como "inicio"
    start_of_time = date(1900, 1, 1)
    
    return await get_account_balances(db, tenant_id, start_of_time, cut_off_date)
    

async def get_period_movements(
    db: AsyncSession, 
    tenant_id: int, 
    start_date: date, 
    end_date: date
) -> List[Dict[str, Any]]:
    """
    Calcula los MOVIMIENTOS NETOS de un periodo específico.
    
    Ideal para el Estado de Resultados (Ganancias y Pérdidas) o Flujo de Efectivo.
    Solo considera lo que ocurrió ENTRE las fechas dadas, ignorando saldos previos.
    
    Args:
        db (AsyncSession): Sesión de base de datos.
        tenant_id (int): ID de la empresa.
        start_date (date): Inicio del periodo fiscal.
        end_date (date): Fin del periodo fiscal.

    Returns:
        List[Dict]: Lista de cuentas con su movimiento neto en ese rango.
    """
    return await get_account_balances(db, tenant_id, start_date, end_date)