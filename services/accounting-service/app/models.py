from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

class AccountType(str, enum.Enum):
    ASSET = "ASSET"         # Activo
    LIABILITY = "LIABILITY" # Pasivo
    EQUITY = "EQUITY"       # Patrimonio
    REVENUE = "REVENUE"     # Ingreso
    EXPENSE = "EXPENSE"     # Gasto
    
class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    # Código Jerárquico
    code = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    
    # Tipo: ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
    account_type = Column(String, nullable=False)
    
    # Nivel de la cuenta: 1 (Grupo), 2 (Rubro), 3 (Cuenta), 4 (Subcuenta)
    level = Column(Integer, default=1)
    
    # ¿Acepta Transacciones? (Las cuentas de nivel superior como "1. ACTIVO" no aceptan, solo sus hijas)
    is_transactional = Column(Boolean, default=True)
    
    parent_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    parent = relationship(
        "Account",
        remote_side=[id],
        back_populates="children",
        foreign_keys=[parent_id]
    )
    
    # Saldo actual
    balance = Column(Numeric(12, 2), default=0)
    is_active = Column(Boolean, default=True)
    
    
    # Relaciones
    children = relationship(
        "Account", 
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        UniqueConstraint('code', 'tenant_id', name='uq_account_code_tenant'),
    )
    

class LedgerEntry(Base):
    """Asiento Contable"""
    __tablename__ = "ledger_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    transaction_date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    reference = Column(String, nullable=True) # ID Factura, Recibo, etc.
    
    # La transacción completa (Debe balancear Débito == Crédito)
    total_amount = Column(Numeric(12, 2), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    #Relación con el detalle
    lines = relationship("LedgerLine", back_populates="entry", cascade="all, delete-orphan")
    
class LedgerLine(Base):
    """El detalle del asiento: Qué cuenta se debita o acredita"""
    __tablename__ = "ledger_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("ledger_entries.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    debit = Column(Numeric(12, 2), default=0)
    credit = Column(Numeric(12, 2), default=0)
    
    entry = relationship("LedgerEntry", back_populates="lines")
    account = relationship("Account")

class TransactionType(str, enum.Enum):
    INCOME = "INCOME"   # Entrada (Ventas)
    EXPENSE = "EXPENSE" # Salida (Gastos, Nómina)
    
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    transaction_type = Column(String, nullable=False)        # INCOME o EXPENSE
    category = Column(String, nullable=False)               # Ventas, Nómina, Alquiler
    amount = Column(Numeric(10, 2), nullable=False)         
    currency = Column(String(3), default="USD")
    
    description = Column(String, nullable=True)
    reference_id = Column(String, nullable=True)            # ID de factura o ID de pago de nómina
    
    created_at = Column(DateTime(timezone=True))