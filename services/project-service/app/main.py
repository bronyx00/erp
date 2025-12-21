from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from . import crud, schemas, database, models
from .schemas import PaginatedResponse
from erp_common.security import RequirePermission, Permissions, UserPayload

# Inicialización DB
async def lifespan(app: FastAPI):
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield

app = FastAPI(
    title="Project Service",
    description="Gestión de Proyectos, Tareas y Tiempos.",
    version="1.0.0",
    root_path="/api/projects",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PROYECTOS ---

@app.get("/", response_model=PaginatedResponse[schemas.ProjectResponse])
async def read_projects(
    page: int = 1,
    limit: int = 20,
    search: str = None,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PROJECT_READ))
):
    """
    **Listar Proyectos**
    
    Devuelve los proyectos de la empresa, incluyendo sus tareas asociadas.
    """
    return await crud.get_projects(db, user.tenant_id, page, limit, search)


@app.post("/", response_model=schemas.ProjectResponse, status_code=201)
async def create_project(
    project: schemas.ProjectCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PROJECT_CREATE))
):
    """**Crear Nuevo Proyecto**"""
    return await crud.create_project(db, project, user.tenant_id)

@app.get("/{project_id}", response_model=schemas.ProjectResponse)
async def read_project(
    project_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PROJECT_READ))
):
    """**Detalle de Proyecto** (con tareas)."""
    project = await crud.get_project_by_id(db, project_id, user.tenant_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project

# --- TAREAS ---

@app.post("/{project_id}/tasks", response_model=schemas.TaskResponse)
async def add_task(
    project_id: int,
    task: schemas.TaskCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.TASK_MANAGE))
):
    """**Agregar Tarea a un Proyecto**"""
    new_task = await crud.create_task(db, project_id, task, user.tenant_id)
    if not new_task:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return new_task

@app.put("/tasks/{task_id}/stage", response_model=schemas.TaskResponse)
async def update_task_stage(
    task_id: int,
    stage: str,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.TASK_MANAGE))
):
    """
    **Actualizar Estado de Tarea**
    
    Útil para tableros Kanban (mover de TODO a DONE).
    """
    task = await crud.update_task_stage(db, task_id, stage, user.tenant_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return task

@app.patch("/tasks/{task_id}/move", response_model=schemas.TaskResponse)
async def move_task(
    task_id: int,
    stage: str, # Recibir como query param ?stage=DONE
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.TASK_MANAGE))
):
    task = await crud.update_task_stage(db, task_id, stage, user.tenant_id)
    if not task:
        raise HTTPException(404, "Tarea no encontrada")
    return task