from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Generic, TypeVar
from datetime import date, datetime

T = TypeVar("T")

# --- UTILIDADES ---

class MetaData(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: MetaData

# --- TAREAS ---

class TaskBase(BaseModel):
    name: str = Field(..., description="Nombre de la tarea")
    description: Optional[str] = None
    stage: str = Field("TODO", description="Estado: TODO, IN_PROGRESS, DONE")
    priority: str = "MEDIUM"
    assigned_to: Optional[int] = None
    deadline: Optional[date] = None
    planned_hours: float = 0.0
    
class TaskCreate(TaskBase):
    pass

class TaskResponse(TaskBase):
    id: int
    project_id: int
    model_config = ConfigDict(from_attributes=True)
    
# --- PROYECTOS ---

class ProjectBase(BaseModel):
    name: str = Field(..., description="Nombre del proyecto")
    description: Optional[str] = None
    client_id: Optional[int] = None
    manager_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: float = 0.0
    status: str = Field("PLANNING", description="Estado: PLANNING, IN_PROGRESS, COMPLETED")
    
class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    tasks: List[TaskResponse] = []
    model_config = ConfigDict(from_attributes=True)