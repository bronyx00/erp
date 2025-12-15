from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date, datetime

# --- TASK ---
class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    stage: str = "TODO"
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
    
# --- PROJECT ---
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    client_id: Optional[int] = None
    manager_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: float = 0.0
    status: str = "ACTIVE"
    
class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    tasks: List[TaskResponse] = []
    model_config = ConfigDict(from_attributes=True)