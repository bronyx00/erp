from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from typing import Optional, List, Generic, TypeVar

T = TypeVar("T")

# GENERIC PAGINATION
class MetaData(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    
class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: MetaData

class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    category: str = "General"
    price: Decimal
    stock: int = 0
    
class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)