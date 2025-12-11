from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Date, Text, JSON, ForeignKey, Time
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class WorkSchedule(Base):
    """Modelo para Turnos/Horarios de Trabajo"""
    __tablename__ = "work_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=True)
    name = Column(String, nullable=False) # Ej: "Diurno Lunes-Viernes"
    
    # Horas (Formato 24h)
    monday_start = Column(Time, nullable=True)
    monday_end = Column(Time, nullable=True)
    tuesday_start = Column(Time, nullable=True)
    tuesday_end = Column(Time, nullable=True)
    wednesday_start = Column(Time, nullable=True)
    wednesday_end = Column(Time, nullable=True)
    thursday_start = Column(Time, nullable=True)
    thursday_end = Column(Time, nullable=True)
    friday_start = Column(Time, nullable=True)
    friday_end = Column(Time, nullable=True)
    saturday_start = Column(Time, nullable=True)
    saturday_end = Column(Time, nullable=True)
    sunday_start = Column(Time, nullable=True)
    sunday_end = Column(Time, nullable=True)
    
    is_active = Column(Boolean, default=True)

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
    manager_name = Column(Integer, nullable=True)     # ID de otro empleado (Supervisor)
    hired_at = Column(Date, nullable=True)
    contract_type = Column(String, default="UNDEFINED") # Indefinido, Determinado
    
    # --- RELACION CON HORARIO ---
    schedule_id = Column(Integer, ForeignKey("work_schedules.id"), nullable=True)
    schedule = relationship("WorkSchedule")
    
    # --- COMPENSACIÓN ---
    salary = Column(Numeric(10, 2), default=0)
    bonus_scheme = Column(String, nullable=True)    # Ej: "3% Comisión"
    
    # --- DATOS COMPLEJOS ---
    emergency_contract = Column(JSON, nullable=True)
    documents = Column(JSON, default=list)
    performance_reviews = Column(JSON, default=list)
    
    # --- ESTADO ---
    status = Column(String, default="Active")       # ACTIVE, ON LEAVE, TERMINATED
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
    