from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .database import Base
import enum

# --- ENUMS ---
class TaxType(str, enum.Enum):
    EXCLUSIVE = "EXCLUSIVE"
    INCLUSIVE = "INCLUSIVE"

class InvoiceFormat(str, enum.Enum):
    TICKET = "TICKET"
    FULL_PAGE = "FULL_PAGE"
    
class CurrencyDisplay(str, enum.Enum):
    VES_ONLY = "VES_ONLY"
    DUAL = "DUAL"
    MIXED_TOTAL = "MIXED_TOTAL"

class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    SALES_AGENT = "SALES_AGENT"
    SALES_SUPERVISOR = "SALES_SUPERVISOR"
    ACCOUNTANT = "ACCOUNTANT"
    WAREHOUSE_CLERK = "WAREHOUSE_CLERK"
    WAREHOUSE_SUPERVISOR = "WAREHOUSE_SUPERVISOR"
    RRHH_MANAGER = "RRHH_MANAGER"
    PROJECT_MANAGER = "PROJECT_MANAGER"

# --- MODELOS ---
class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    
    # Datos Fiscales
    rif = Column(String, nullable=False)
    business_name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    
    # Preferencias
    invoice_format = Column(SQLEnum(InvoiceFormat), default=InvoiceFormat.TICKET)
    currency_display = Column(SQLEnum(CurrencyDisplay), default=CurrencyDisplay.VES_ONLY)
    current_local_id = Column(String, default="CASA MATRIZ")
    
    # Configuración Fiscal
    tax_active = Column(Boolean, default=True)
    tax_type = Column(SQLEnum(TaxType), default=TaxType.EXCLUSIVE)
    tax_rate = Column(Integer, default=16)
    
    plan = Column(String, default="BASIC")
    is_active = Column(Boolean, default=True)
    
    users = relationship("User", back_populates="tenant")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default=UserRole.OWNER.value, nullable=False)
    
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="users")