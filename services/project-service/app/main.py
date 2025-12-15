from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from . import crud, schemas, database, models
from .security import RequirePermission, Permissions, UserPayload

async def lifespan(app: FastAPI):
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield

app = FastAPI(title="Project Service", root_path="/api/projects", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/", response_model=schemas.ProjectResponse)
async def create_project(
    project: schemas.ProjectCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PROJECT_CREATE))
):
    return await crud.create_project(db, project, user.tenant_id)

@app.get("/", response_model=List[schemas.ProjectResponse])
async def read_projects(
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.PROJECT_READ))
):
    return await crud.get_projects(db, user.tenant_id)

@app.post("/{project_id}/tasks", response_model=schemas.TaskResponse)
async def add_task(
    project_id: int,
    task: schemas.TaskCreate,
    db: AsyncSession = Depends(database.get_db),
    user: UserPayload = Depends(RequirePermission(Permissions.TASK_MANAGE))
):
    new_task = await crud.create_task(db, project_id, task, user.tenant_id)
    if not new_task:
        raise HTTPException(404, "Proyecto no encontrado")
    return new_task

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