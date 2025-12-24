from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any
from . import models, schemas
from datetime import datetime

async def check_employee_access(db: AsyncSession, email: str, tenant_id: int) -> bool:
    """
    Verifica si un empleado tiene permitido el acceso al sistema en este momento
    basándose en su Horario de Trabajo asignado.
    """
    # 1. Buscar empleado y cargar su horario
    query = select(models.Employee).options(selectinload(models.Employee.schedule))\
        .filter(models.Employee.email == email, models.Employee.tenant_id == tenant_id)
        
    result = await db.execute(query)
    employee = result.scalars().first()
    
    # 2. Si no tiene horario restringido o no existe, permitimos acceso (Fail-open para dueños/admins)
    if not employee or not employee.schedule or not employee.schedule.is_active:
        return True
    
    # 3. Determinar momento actual
    now = datetime.now()
    current_time = now.time()
    weekday = now.weekday() # 0=Lunes, 1=Martes, ...., 6=Domingo
    
    # 4. Mapeo de campos del modelo WorkSchedule
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
    
    # 5. Reglas de Validación
    # Si el dia no tiene horas definidas (None), es dia libre -> ACCESO DENEGADO
    if start is None or end is None:
        return False
    
    # Si la hora actual está dentro del rango -> ACCESO PERMITIDO
    if start <= current_time <= end:
        return True
    
    return False

async def get_employees(db: AsyncSession, tenant_id: int, page: int = 1, limit: int = 50):
    """Lista paginada de empleados."""
    offset = (page - 1) * limit
    conditions = [models.Employee.tenant_id == tenant_id]

    # Conteo Optimizado
    count_query = select(func.count(models.Employee.id)).filter(*conditions)
    total = (await db.execute(count_query)).scalar() or 0
    
    # Consulta de datos
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
    """Crea un nuevo empleado."""
    # Sanitización 
    schedule_id_val = employee.schedule_id if employee.schedule_id and employee.schedule_id > 0 else None
    manager_id_val = employee.manager_id if employee.manager_id and employee.manager_id > 0 else None
    
    # Procesamiento de campos JSON
    emergency_contact_data = {}
    if employee.emergency_contact:
        if hasattr(employee.emergency_contact, 'model_dump'):
            emergency_contact_data = employee.emergency_contact.model_dump()
        elif hasattr(employee.emergency_contact, 'dict'): 
            emergency_contact_data = employee.emergency_contact.dict()
        else:
            emergency_contact_data = employee.emergency_contact
            
    document_data = []
    if employee.documents:
        # Procesamos la lista
        documents_data = [
            doc.model_dump() if hasattr(doc, 'model_dump') else (doc.dict() if hasattr(doc, 'dict') else doc)
            for doc in employee.documents
        ]
    
    reviews_data = []
    if employee.performance_reviews:
        reviews_data = [
            rev.model_dump() if hasattr(rev, 'model_dump') else (rev.dict() if hasattr(rev, 'dict') else rev)
            for rev in employee.performance_reviews
        ]
    
    db_employee = models.Employee(
        tenant_id=tenant_id,
        first_name=employee.first_name,
        last_name=employee.last_name,
        identification=employee.identification,
        email=employee.email,
        phone=employee.phone,
        address=employee.address,
        birth_date=employee.birth_date,
        hired_at=employee.hired_at,
        position=employee.position,
        department=employee.department,
        salary=employee.salary,
        contract_type=employee.contract_type,
        bonus_scheme=employee.bonus_scheme,
        emergency_contact=emergency_contact_data,
        documents=document_data,
        performance_reviews=reviews_data,
        status="Active",
        is_active=True,
        manager_id=manager_id_val,
        schedule_id=schedule_id_val
    )
    db.add(db_employee)
    await db.commit()
    
    query = (
        select(models.Employee)
        .options(
            selectinload(models.Employee.schedule),
            selectinload(models.Employee.manager)
        )
        .filter(models.Employee.id == db_employee.id)
    )
    result = await db.execute(query)
    db_employee = result.scalars().first()
    
    return db_employee

async def get_employee_by_id(db: AsyncSession, employee_id: int, tenant_id: int):
    """Busca empleado por ID con su horario cargado."""
    query = select(models.Employee).filter(
        models.Employee.id == employee_id,
        models.Employee.tenant_id == tenant_id
    ).options(selectinload(models.Employee.schedule))
    result = await db.execute(query)
    return result.scalars().first()

async def update_employee (
    db: AsyncSession,
    employee_id: int,
    employee_update: schemas.EmployeeUpdate,
    tenant_id: int
):
    """Actualiza datos parciales de un empleado."""
    # Busca al empleado existente
    db_employee = await get_employee_by_id(db, employee_id, tenant_id)
    if not db_employee:
        return None
    
    # Actualiza solo los campos que vienen en el JSON
    update_data = employee_update.model_dump(exclude_unset=True)
    
    if 'manager_id' in update_data and update_data['manager_id'] == 0:
        update_data['manager_id'] = None
        
    if 'schedule_id' in update_data and update_data['schedule_id'] == 0:
        update_data['schedule_id'] = None

    if 'emergency_contact' in update_data and update_data['emergency_contact']:
         if hasattr(update_data['emergency_contact'], 'model_dump'):
             update_data['emergency_contact'] = update_data['emergency_contact'].model_dump()
         elif hasattr(update_data['emergency_contact'], 'dict'):
             update_data['emergency_contact'] = update_data['emergency_contact'].dict()
    
    for key, value in update_data.items():
        setattr(db_employee, key, value)
        
    # Guarda los cambios
    db.add(db_employee)
    await db.commit()
    await db.refresh(db_employee)
    return db_employee

# --- HORARIOS ---

async def create_schedule(db: AsyncSession, schedule: schemas.WorkScheduleCreate, tenant_id: int):
    """Crea el horario general de la empresa"""
    db_schedule = models.WorkSchedule(
        tenant_id=tenant_id,
        **schedule.model_dump()
    )
    db.add(db_schedule)
    await db.commit()
    await db.refresh(db_schedule)
    return db_schedule

async def get_schedule(db: AsyncSession, tenant_id: int):
    """Obtiene el horario de la empresa"""
    query = select(models.WorkSchedule).filter(
        models.WorkSchedule.tenant_id == tenant_id,
        models.WorkSchedule.is_active == True
    )
    result = await db.execute(query)
    return result.scalars().all()

# --- NÓMINA ---

async def create_payroll(db: AsyncSession, payroll_data: schemas.PayrollCreate, tenant_id: int):
    """
    Genera una nómina GLOBAL para todos los empleados activos.
    
    NOTA: Esto es una versión simplificada. En un sistema real, 
    esto iteraría empleado por empleado calculando deducciones.
    """
    # Calcular el total a pagar (Suma de salarios de activos)
    query_sum = select(func.sum(models.Employee.salary)).filter(
        models.Employee.tenant_id == tenant_id,
        models.Employee.is_active == True
    )
    result_sum = await db.execute(query_sum)
    total_amount = result_sum.scalar() or 0
    
    if total_amount == 0:
        raise ValueError("No hay empleados activos o salarios para procesar.")
    
    employees = await get_employees(db, tenant_id, limit=1000)
    created_payrolls = []
    
    # Iteración para crear el pago de TODOS los empleados 
    for emp in employees['data']:
        payroll = models.Payroll(
            tenant_id=tenant_id,
            employee_id=emp.id,
            period_start=payroll_data.period_start,
            period_end=payroll_data.period_end,
            
            base_salary=emp.salary,
            total_earning=emp.salary,
            net_pay=emp.salary,
            
            status="APPROVED"
        )
        db.add(payroll)
        created_payrolls.append(payroll)
        
    await db.commit()
    await db.refresh(payroll)
    
    return created_payrolls

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
    count_query = select(func.count(models.SupervisorNote.id)).filter(*conditions)
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
    
