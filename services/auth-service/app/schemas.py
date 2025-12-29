from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Generic, TypeVar
from .models import UserRole

T = TypeVar("T")

# --- GENÉRICOS ---
class MetaData(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: MetaData

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

class TenantResponse(TenantBase):
    id: int
    plan: str
    model_config = ConfigDict(from_attributes=True)

# --- USER ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

# Schema exclusivo para el registro inicial (Dueño + Empresa)
class OnboardingRequest(UserBase):
    password: str
    company_name: str
    company_rif: str
    company_address: str
    company_business_name: str

# Schema para crear empleados internos
class UserCreateInternal(UserBase):
    password: str
    role: UserRole

class UserResponse(UserBase):
    id: int
    email: str
    is_active: bool
    role: str
    tenant_id: int
    tenant: TenantResponse
    model_config = ConfigDict(from_attributes=True)

# --- AUTH ---
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    
class RefreshTokenRequest(BaseModel):
    refresh_token: str