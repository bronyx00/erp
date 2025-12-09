from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from typing import Optional

class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    category: str
    price: Decimal
    stock: int = 0
    
class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)