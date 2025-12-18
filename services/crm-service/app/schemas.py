from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional, List, Generic, TypeVar
from datetime import datetime

T = TypeVar("T")

class MetaData(BaseModel):
    """Metadatos para respuestas paginadas."""
    total: int
    page: int
    limit: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    """Estructura genérica para devolver listas paginadas."""
    data: List[T]
    meta: MetaData

class CustomerBase(BaseModel):
    """Datos base del cliente compartidos entre creación y lectura."""
    name: str = Field(..., description="Nombre o Razón Social del cliente")
    email: Optional[EmailStr] = Field(None, description="Correo electrónico de contacto")
    tax_id: Optional[str] = Field(None, description="Documento de identidad fiscal (RIF/NIT/Cédula)")
    phone: Optional[str] = None
    address: Optional[str] = None
    
class CustomerCreate(CustomerBase):
    """Esquema para crear un nuevo cliente."""
    pass

class CustomerResponse(CustomerBase):
    """Esquema de respuesta completo con datos del sistema."""
    id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)