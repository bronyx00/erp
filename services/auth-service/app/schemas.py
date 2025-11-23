from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional

class TenantBase(BaseModel):
    name: str

class TenantCreate(TenantBase):
    """Datos necesarios para registrar una nueva empresa."""
    
class TenantResponse(TenantBase):
    id: int
    plan: str
    model_config = ConfigDict(from_attributes=True)

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    """
    Datos para registrar al DUEÑO inicial.
    Incluye el nombre de la empresa que está fundando.
    """
    password: str
    company_name: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    role: str
    tenant_id: int
    tenant: TenantResponse

    # Configuración para leer desde modelos ORM (SQLAlchemy)
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str