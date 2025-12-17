from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from . import models, schemas
from datetime import datetime

async def check_employee_access(db: AsyncSession, email: str, tenant_id: int) -> bool:
    """Verifica si el empleado puede acceder según su horarioactual"""
    # Buscar empleado y su horario
    query = select(models.Employee).options(selectinload(models.Employee.schedule))\
        .filter(models.Employee.email == email, models.Employee.tenant_id == tenant_id)
        
    result = await db.execute(query)
    employee = result.scalars().first()
    
    # Si no existe en nómina o no tiene horario asignado, permitimos acceso
    # Si no tiene horario restringido, entra libremente.
    if not employee or not employee.schedule or not employee.schedule.is_active:
        return True
    
    # Determinar día y hora actual
    now = datetime.now()
    current_time = now.time()
    weekday = now.weekday() # 0=Lunes, 1=Martes, ...., 6=Domingo
    
    # Mapeo de los campos del modelo WorkSchedule
    sched = employee.schedule
    # (inicio, fin) para cada día
    day_map = {
        0: (sched.monday_start, sched.monday_end),
        1: (sched.tuesday_start, sched.tuesday_end),
        2: (sched.wednesday_start, sched.wednesday_end),
        3: (sched.thursday_start, sched.thursday_end),
        4: (sched.friday_start, sched.friday_end),
        5: (sched.saturday_start, sched.saturday_end),
        6: (sched.sunday_start, sched.sunday_end),
    }
    
    start, end = day_map.get(weekday, (None, None))
    
    # Validar Relas 
    # Si el dia no tiene horas definidas (None), es dia libre -> ACCESO DENEGADO
    if start is None or end is None:
        return False
    
    # Si la hora actual está dentro del rango -> ACCESO PERMITIDO
    if start <= current_time <= end:
        return True
    
    return False

async def get_employees(db: AsyncSession, tenant_id: int, page: int = 1, limit: int = 50):
    offset = (page - 1) * limit
    conditions = [models.Employee.tenant_id == tenant_id]

    # Conteo Rápido
    count_query = select(func.count(models.Employee.id)).filter(*conditions)
    total = (await db.execute(count_query)).scalar() or 0
    
    query = (
        select(models.Employee)
        .filter(*conditions)
        .order_by(models.Employee.last_name.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    
    return {
        "data": result.scalars().all(),
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if limit > 0 else 0
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

# --- NOTAS ---
async def create_note(
    db: AsyncSession,
    note: schemas.SupervisorNoteCreate,
    supervisor_email: str,
    tenant_id: int
):
    db_note = models.SupervisorNote(
        tenant_id=tenant_id,
        employee_id=note.employee_id,
        supervisor_email=supervisor_email,
        category=note.category,
        content=note.content,
        is_private=note.is_private
    )
    db.add(db_note)
    await db.commit()
    await db.refresh(db_note)
    return db_note

async def get_employee_notes(
    db: AsyncSession,
    employee_id: int,
    tenant_id: int,
    page: int = 1,
    limit: int = 10
):
    offset = (page - 1) * limit
    
    conditions = [models.SupervisorNote.employee_id == employee_id, models.SupervisorNote.tenant_id == tenant_id]
    
    # Contar total
    count_query = select(func.count(models.SupervisorNote)).filter(*conditions)
    total = (await db.execute(count_query)).scalar() or 0
    
    query = (
        select(models.SupervisorNote)
        .filter(*conditions)
        .order_by(models.SupervisorNote.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    
    return {
        "data": result.scalars().all(),
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if limit > 0 else 0
        }
    }
    
async def update_employee (
    db: AsyncSession,
    employee_id: int,
    employee_update: schemas.EmployeeUpdate,
    tenant_id: int
):
    # Busca al empleado existente
    db_employee = await get_employee_by_id(db, employee_id, tenant_id)
    if not db_employee:
        return None
    
    # Actualiza solo los campos que vienen en el JSON
    update_data = employee_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_employee, key, value)
        
    # Guarda los cambios
    await db.commit()
    await db.refresh(db_employee)
    return db_employee