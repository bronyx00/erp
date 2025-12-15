from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    client_id = Column(Integer, nullable=True) # ID del cliente en CRM
    manager_id = Column(Integer, nullable=True) # ID del Project Manager (User)
    
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    
    status = Column(String, default="ACTIVE") # ACTIVE, ARCHIVED, COMPLETED
    
    # Presupuesto (Opcional, para conectar con Finance luego)
    budget = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Kanban Stage (Ej: "Por hacer", "En Progreso", "Listo")
    stage = Column(String, default="TODO") 
    priority = Column(String, default="MEDIUM") # LOW, MEDIUM, HIGH
    
    assigned_to = Column(Integer, nullable=True) # User ID del empleado
    
    deadline = Column(Date, nullable=True)
    
    # Estimación
    planned_hours = Column(Float, default=0.0)
    
    project = relationship("Project", back_populates="tasks")