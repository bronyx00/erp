from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from typing import Optional, List, Generic, TypeVar

T = TypeVar("T")

# --- UTILIDADES ---

class MetaData(BaseModel):
    """Metadatos de paginación."""
    total: int
    page: int
    limit: int
    total_pages: int
    
class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta genérica paginada."""
    data: List[T]
    meta: MetaData
    
# --- PRODUCTOS ---

class ProductBase(BaseModel):
    """Datos base del producto."""
    sku: str = Field(..., description="Código único del producto (SKU)")
    name: str = Field(..., description="Nombre del producto")
    description: Optional[str] = None
    category: str = Field("General", description="Categoría (ej. Servicios, Hardware)")
    price: Decimal = Field(..., gt=0, description="Precio unitario (debe ser mayor a 0)")
    stock: int = Field(0, ge=0, description="Stock inicial (debe ser mayor o igual a 0)")
    
class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    """Respuesta completa del producto."""
    id: int
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)