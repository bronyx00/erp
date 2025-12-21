from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from typing import Optional, Dict, Any
from . import models, schemas

async def get_projects(db: AsyncSession, 
    tenant_id: int, 
    page: int = 1, 
    limit: int = 20,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Obtiene lista de proyectos con sus tareas cargadas.
    """
    offset = (page - 1) * limit
    conditions = [models.Project.tenant_id == tenant_id]
    
    if search:
        conditions.append(models.Project.name.ilike(f"%{search}%"))
        
    # 1. Conteo Rápido
    count_query = select(func.count(models.Project.id)).filter(*conditions)
    total = (await db.execute(count_query)).scalar() or 0
    
    # 2. Obtener Datos
    query = (
        select(models.Project)
        .options(selectinload(models.Project.tasks))
        .filter(*conditions)
        .order_by(models.Project.start_date.desc())
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

async def create_project(
    db: AsyncSession, 
    project: schemas.ProjectCreate, 
    tenant_id: int
):
    """Crea un nuevo proyecto."""
    db_project = models.Project(tenant_id=tenant_id, **project.model_dump())
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    
    project_dict = db_project.__dict__
    return schemas.ProjectResponse(
        **project_dict,
        tasks=[]
    )

async def get_project_by_id(db: AsyncSession, project_id: int, tenant_id: int):
    """Busca proyecto por ID y carga sus tareas."""
    query = (
        select(models.Project)
        .options(selectinload(models.Project.tasks))
        .filter(models.Project.id == project_id, models.Project.tenant_id == tenant_id)
    )
    result = await db.execute(query)
    return result.scalars().first()

# -- TAREAS ---

async def create_task(
    db: AsyncSession, 
    project_id: int, 
    task: schemas.TaskCreate, 
    tenant_id: int
):
    """Agrega una tarea a un proyecto existente."""
    # Verificar que el proyecto pertenezca a la empresa
    project = await get_project_by_id(db, project_id, tenant_id)
    if not project:
        return None
    
    db_task = models.Task(
        **task.model_dump(),
        project_id=project_id
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

async def update_task_stage(
    db: AsyncSession,
    task_id: int,
    new_stage: str,
    tenant_id: int
):
    """Actualiza el estado de una tarea (Drag & Drop en Kanban)."""
    # Join con Project para asegurar tenant_id
    query = select(models.Task).join(models.Project).filter(
        models.Task.id == task_id,
        models.Project.tenant_id == tenant_id
    )
    result = await db.execute(query)
    task = result.scalars().first()
    
    if not task:
        return None
    
    task.stage = new_stage
    await db.commit()
    await db.refresh(task)
    return task