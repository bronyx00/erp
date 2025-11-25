from sqlalchemy.ext.asyncio import AsyncSession
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