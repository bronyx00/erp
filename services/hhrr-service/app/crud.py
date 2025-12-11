from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from . import models, schemas

async def get_employees(db: AsyncSession, tenant_id: int, page: int = 1, limit: int = 50):
    offset = (page - 1) * limit
    
    query = select(models.Employee).filter(
        models.Employee.tenant_id == tenant_id,
        models.Employee.is_active == True
    ).options(selectinload(models.Employee.schedule))
    
    # Contar Total
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0
    
    # Obtiene Datos Paginados
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    data = result.scalars().all()
    
    return {
        "data": data,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }
    }

async def create_employee(db: AsyncSession, employee: schemas.EmployeeCreate, tenant_id: int):
    db_employee = models.Employee(
        tenant_id=tenant_id,
        **employee.model_dump()
    )
    db.add(db_employee)
    await db.commit()
    await db.refresh(db_employee)
    return db_employee

async def create_schedule(db: AsyncSession, schedule: schemas.WorkScheduleCreate, tenant_id: int):
    db_schedule = models.WorkSchedule(
        tenant_id=tenant_id,
        **schedule.model_dump()
    )
    db.add(db_schedule)
    await db.commit()
    await db.refresh(db_schedule)
    return db_schedule

async def get_schedule(db: AsyncSession, tenant_id: int):
    query = select(models.WorkSchedule).filter(
        models.WorkSchedule.tenant_id == tenant_id,
        models.WorkSchedule.is_active == True
    )
    result = await db.execute(query)
    return result.scalars().all()

async def get_employee_by_id(db: AsyncSession, employee_id: int, tenant_id: int):
    query = select(models.Employee).filter(
        models.Employee.id == employee_id,
        models.Employee.tenant_id == tenant_id
    ).options(selectinload(models.Employee.schedule))
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