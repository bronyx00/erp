from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Date, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from .database import Base

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    # --- DATOS PERSONALES ---
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    identification = Column(String, nullable=False, index=True) 
    email = Column(String, index=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    birth_date = Column(Date, nullable=True)
    
    # --- DATOS LABORALES ---
    position = Column(String) 
    departament = Column(String, nullable=True)     # Ej: Ventas, Almacén
    manager_id = Column(Integer, nullable=True)     # ID de otro empleado (Supervisor)
    salary = Column(Numeric(10, 2), default=0)      # Sueldo Mensual
    bonus_scheme = Column(String, nullable=True)    # Ej: "3% Comisión"
    hired_at = Column(Date, nullable=True)
    contract_type = Column(String, default="UNDEFINED") # Indefinido, Determinado
    
    # --- DATOS EMERGENCIA ---
    emergency_contract = Column(JSON, nullable=True)
    
    # --- ESTADO ---
    status = Column(String, default="ACTIVE")       # ACTIVE, ON LEAVE, TERMINATED
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
class Payroll(Base):
    __tablename__ = "payrolls"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String, default="PAID")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    