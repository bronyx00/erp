from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from . import models, schemas

async def create_project(db: AsyncSession, project: schemas.ProjectCreate, tenant_id: int):
    db_project = models.Project(tenant_id=tenant_id, **project.model_dump())
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project

async def get_projects(db: AsyncSession, tenant_id: int):
    # Cargar tareas para el tablero
    query = select(models.Project)\
        .options(selectinload(models.Project.tasks))\
            .filter(models.Project.tenant_id == tenant_id)\
                .order_by(models.Project.id.desc())
                
    result = await db.execute(query)
    return result.scalars().all()

async def create_task(db: AsyncSession, project_id: int, task: schemas.TaskCreate, tenant_id: int):
    # Verificar que el proyecto pertenezca al tenant
    proj = await db.get(models.Project, project_id)
    if not proj or proj.tenant_id != tenant_id:
        return None
    
    db_task = models.Task(project_id=project_id, **task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

async def update_task_stage(db: AsyncSession, task_id: int, new_stage: str, tenant_id: int):
    # Buscr tarea asegurando tenant a través del proyecto
    query = select(models.Task).join(models.Project).filter(
        models.Task.id == task_id,
        models.Project.tenant_id == tenant_id
    )
    result = await db.execute(query)
    task = result.scalars().first()
    
    if task:
        task.stage = new_stage
        await db.commit()
        await db.refresh(task)
    return task