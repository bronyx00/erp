from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Date
from sqlalchemy.sql import func
from .database import Base

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    # Datos Personales
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    identification = Column(String, nullable=False) # ID
    email = Column(String, index=True)
    phone = Column(String, nullable=True)
    
    # Datos Laborales
    position = Column(String) # Cargo
    salary = Column(Numeric(10, 2), default=0) # Sueldo Mensual
    hired_at = Column(Date, nullable=True) # Fecha ingreso
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    