from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Generic, TypeVar
from datetime import datetime

T = TypeVar("T")

class MetaData(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: MetaData

class CustomerBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    
class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)