from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional

# --- TENANT ---
class TenantBase(BaseModel):
    name: str
    business_name: Optional[str] = None
    rif: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    tax_active: bool = True
    invoice_format: str = "TICKET"
    currency_display: str = "VES_ONLY"
    tax_rate: int = 16

class TenantCreate(TenantBase):
    """Datos necesarios para registrar una nueva empresa."""
    pass
    
class TenantResponse(TenantBase):
    id: int
    plan: str
    model_config = ConfigDict(from_attributes=True)


# --- USER ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    """
    Datos para registrar al DUEÑO inicial.
    Incluye el nombre de la empresa que está fundando.
    """
    full_name: str              # Nombre completo del dueño
    password: str
    # Datos de la empresa
    company_name: str           # Nombre Comercial
    company_rif: str            # RIF Obligatorio
    company_address: str        # Dirección Obligatoria
    company_business_name: str  # Razón Social

class SubUserCreate(UserBase):
    """Creación de empleados."""
    password: str
    role: str

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
    
class TokenPayload(BaseModel):
    """Para validar el token internamente."""
    sub: str
    role: str
    tenant_id: int