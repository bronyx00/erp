from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select
from . import models, schemas

async def get_employees(db: AsyncSession, tenant_id: int):
    query = select(models.Employee).filter(
        models.Employee.tenant_id == tenant_id,
        models.Employee.is_active == True
    )
    result = await db.execute(query)
    return result.scalars().all()

async def create_employee(db: AsyncSession, employee: schemas.EmployeeCreate, tenant_id: int):
    db_employee = models.Employee(
        **employee.model_dump(),
        tenant_id=tenant_id
    )
    db.add(db_employee)
    await db.commit()
    await db.refresh(db_employee)
    return db_employee

async def get_employee_by_id(db: AsyncSession, employee_id: int, tenant_id: int):
    query = select(models.Employee).filter(
        models.Employee.id == employee_id,
        models.Employee.tenant_id == tenant_id
    )
    result = await db.execute(query)
    return result.scalars().first()

async def create_payroll(db: AsyncSession, payroll_data: schemas.PayrollCreate, tenant_id: int):
    # Calcular el total a pagar (Suma de salarios de activos)
    query_sum = select(func.sum(models.Employee.salary)).filter(
        models.Employee.tenant_id == tenant_id,
        models.Employee.is_active == True
    )
    result_sum = await db.execute(query_sum)
    total_amount = result_sum.scalar() or 0
    
    if total_amount == 0:
        raise ValueError("No hay empleados activos o salarios para procesar.")
    
    # Crear el registro de Nómina
    db_payroll = models.Payroll(
        tenant_id=tenant_id,
        period_start=payroll_data.period_start,
        period_end=payroll_data.period_end,
        total_amount=total_amount,
        status="PAID"
    )
    db.add(db_payroll)
    await db.commit()
    await db.refresh(db_payroll)
    
    return db_payroll