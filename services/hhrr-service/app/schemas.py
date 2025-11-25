from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from decimal import Decimal
from datetime import date, datetime

class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    identification: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    salary: Decimal = Decimal(0)
    hired_at: Optional[date] = None
    
class EmployeeCreate(EmployeeBase):
    pass

class EmployeeResponse(EmployeeBase):
    id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)