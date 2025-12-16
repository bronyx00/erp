from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Any, Generic, TypeVar
from decimal import Decimal
from datetime import date, datetime, time

T = TypeVar("T")

class MetaData(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: MetaData
    
class WorkScheduleBase(BaseModel):
    name: str
    monday_start: Optional[time] = None
    monday_end: Optional[time] = None
    tuesday_start: Optional[time] = None
    tuesday_end: Optional[time] = None
    wednesday_start: Optional[time] = None
    wednesday_end: Optional[time] = None
    thursday_start: Optional[time] = None
    thursday_end: Optional[time] = None
    friday_start: Optional[time] = None
    friday_end: Optional[time] = None
    saturday_start: Optional[time] = None
    saturday_end: Optional[time] = None
    sunday_start: Optional[time] = None
    sunday_end: Optional[time] = None

class WorkScheduleCreate(WorkScheduleBase):
    pass

class WorkScheduleResponse(WorkScheduleBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class EmergencyContact(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    relationship: Optional[str] = None

class Document(BaseModel):
    name: str
    type: str
    url: str
    uploaded_date: Optional[datetime] = None
    
class PerformanceReview(BaseModel):
    date: date
    rating: int
    summary: str

class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    identification: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[date] = None
    
    position: str
    department: Optional[str] = None
    manager_id: Optional[str] = None
    hired_at: Optional[date] = None
    schedule_id: Optional[int] = None
    
    salary: Decimal = Decimal(0)
    bonus_scheme: Optional[str] = None
    
    # Campos JSON complejos
    emergency_contact: Optional[EmergencyContact] = None
    documents: List[Document] = []
    performance_reviews: List[PerformanceReview] = []
    
    status: str = 'Active'
    
    
class EmployeeCreate(EmployeeBase):
    pass

class EmployeeResponse(EmployeeBase):
    id: int
    is_active: bool
    created_at: datetime
    schedule: Optional[WorkScheduleResponse] = None
    
    model_config = ConfigDict(from_attributes=True)
    
# --- NOMINA ---
class PayrollCreate(BaseModel):
    period_start: date
    period_end: date
    # En el futuro añadir bonos, extras, etc
    
class PayrollResponse(BaseModel):
    id: int
    period_start: date
    period_end: date
    total_amount: Decimal
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
    
# --- NOTAS ---
class SupervisorNoteCreate(BaseModel):
    employee_id: int
    category: str = "GENERAL" 
    content: str
    is_private: bool = False
    
class SupervisorNoteResponse(BaseModel):
    id: int
    supervisor_email: str
    category: str
    content: str
    is_private: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)