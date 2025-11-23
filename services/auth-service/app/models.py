from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .database import Base
import enum

class UserRole(str, enum.Enum):
    OWNER = "OWNER"             # Dueño absoluto (Empresa)
    ADMIN = "ADMIN"             # Puede gestionar usuarios 
    CASHIER = "CASHIER"         # Solo puede facturar
    RRHH = "RRHH"               # Solo ve módulo de RRHH
    ACCOUNTANT = "ACCOUNTANT"   # Solo ve reportes

class Tenant(Base):
    """
    Representa a la Empresa/Negocio.
    Todos los datos del sistema (facturas, productos) pertenecerána un Tenant ID.
    """
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False) # Nombre de la empresa
    plan = Column(String, default="BASIC") # Plan contratado por la empresa
    is_activce = Column(Boolean, default=True)
    
    users = relationship("User", back_populates="tenant")

class User(Base):
    """
    Representa a un empleado dentro del sistema
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    
    role = Column(String, default=UserRole.OWNER, nullable=False)
    
    # A qué empresa pertenece este usuario
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    
    tenant = relationship("Tenant", back_populates="users")