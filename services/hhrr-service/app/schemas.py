from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional, List, Generic, TypeVar
from decimal import Decimal
from datetime import date, datetime, time

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
    
# --- HORARIOS ---
    
class WorkScheduleBase(BaseModel):
    """
    Tabla de horarios del negocio.
    Necesario para clausurar horarios de login de los empleados.
    """
    name: str = Field(..., description="Nombre del turno (ej. Diurno)")
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

# --- SUBMODELOS EMPLEADO ---

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
    
# --- EMPLEADO ---

class EmployeeBase(BaseModel):
    """Información básica de un empleado"""
    first_name: str
    last_name: str
    identification: str = Field(..., description="Cédula de identidad")
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[date] = None
    
    position: str
    department: Optional[str] = None
    manager_id: Optional[int] = None
    hired_at: Optional[date] = None
    schedule_id: Optional[int] = None
    
    salary: Decimal = Field(Decimal(0), description="Salario base")
    bonus_scheme: Optional[str] = None
    
    # Campos JSON complejos
    emergency_contact: Optional[EmergencyContact] = None
    documents: List[Document] = []
    performance_reviews: List[PerformanceReview] = []
    
    status: str = 'Active'
    
    
class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    """Campos opcionales para actualizar un empleado"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    identification: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[date] = None
    position: Optional[str] = None
    department: Optional[str] = None
    manager_id: Optional[int] = None
    hired_at: Optional[date] = None
    schedule_id: Optional[int] = None  
    salary: Optional[Decimal] = None
    bonus_scheme: Optional[str] = None
    emergency_contact: Optional[EmergencyContact] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None

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
    # Aquí podríamos agregar lista de IDs para pagar solo a algunos, o dejarlo global
    
class PayrollResponse(BaseModel):
    id: int
    period_start: date
    period_end: date
    total_amount: Decimal = Field(..., alias="total_earnings")
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