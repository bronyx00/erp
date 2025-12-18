from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base

class Customer(Base):
    """
    Modelo que representa a un Cliente (Customer) en el sistema.
    
    Attributes:
        tenant_id: ID de la empresa a la que pertenece este cliente (Multi-tenancy).
        tax_id: Identificador fiscal (RIF, Cédula, NIT) único por empresa.
    """
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    email = Column(String, index=True)
    tax_id = Column(String) # RIF, Cedula o NIT
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    