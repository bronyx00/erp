from sqlalchemy import Column, Integer, String, Numeric, Boolean
from .database import Base
import enum

class MeasurementUnit(str, enum.Enum):
    UNIT = "UNIT"       # Unidad / Pieza
    KG = "KG"           # Kilogramos
    METER = "METER"     # Metros
    LITER = "LITER"     # Litros
    SERVICE = "SERVICE" # Horas / Servicios

class Product(Base):
    """
    Representa un producto o servicio en el inventario.
    
    Attributes:
        sku: Stock Keeping Unit (Código único de referencia).
        price: Precio unitario de venta.
        stock: Cantidad actual disponible.
    """
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    sku = Column(String, unique=True, index=True, nullable=False) # Código único
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    
    category = Column(String, index=True, default="General")
    
    # Unidad de medida (Por defecto Unidad)
    measurement_unit = Column(String, default="UNIT")
    
    price = Column(Numeric(10, 2), nullable=False) # Precio unitario en USD
    stock = Column(Numeric(12,), default=0) # Cantidad disponible
    is_active = Column(Boolean, default=True)