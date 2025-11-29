from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .database import Base
import enum

class TaxType(str, enum.Enum):
    EXCLUSIVE = "EXCLUSIVE" # El precio base NO incluye IVA ( Precio + IVA )
    INCLUSIVE = "INCLUSIVE" # El precio base YA inclute IVA (Desglosar al facturar)

# Enums para las preferencias
class InvoiceFormat(str, enum.Enum):
    TICKET = "TICKET"
    FULL_PAGE = "FULL_PAGE"
    
class CurrencyDisplay(str, enum.Enum):
    VES_ONLY = "VES_ONLY"       # Todo en Bolivares
    DUAL = "DUAL"               # Muestra Bs y $ en cada línea
    MIXED_TOTAL = "MIXED_TOTAL" # Líneas en BS, Total final muestra ref en $

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
    name = Column(String, index=True, nullable=False)   # Nombre de la empresa
    
    # ---- DATOS FISCALES ----
    rif = Column(String, nullable=False)                 # Ej: J-12345678-9
    business_name = Column(String, nullable=False)       # Razón Social
    address = Column(String, nullable=False)             # Dirección fiscal
    phone = Column(String, nullable=True)
    
    # ---- PREFERENCIAS DE FACTURACIÖN ----
    invoice_format = Column(SQLEnum(InvoiceFormat), default=InvoiceFormat.TICKET)
    currency_display = Column(SQLEnum(CurrencyDisplay), default=CurrencyDisplay.VES_ONLY)
    
    # Campo simple para manejar sucursales por ahora (Cambiar luego por tabla)
    current_local_id = Column(String, default="CASA MATRIZ")
    
    # ---- CONFIGURACIÓN DE FACTURACIÓN ----
    # ¿Cobramos IVA?
    tax_active = Column(Boolean, default=True)
    # ¿El precio del inventario ya tiene IVA o se le suma?
    tax_type = Column(SQLEnum(TaxType), default=TaxType.EXCLUSIVE)
    # Tasa de impuesto (16% estándar)
    tax_rate = Column(Integer, default=16)
    
    plan = Column(String, default="BASIC")              # Plan contratado por la empresa
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