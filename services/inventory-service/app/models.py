from sqlalchemy import Column, Integer, String, Numeric, Boolean
from .database import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    sku = Column(String, unique=True, index=True, nullable=False) # Código único
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Numeric(10, 2), nullable=False) # Precio unitario en USD
    stock = Column(Integer, default=0) # Cantidad disponible
    is_active = Column(Boolean, default=True)