from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum
from sqlalchemy.sql import func
from .database import Base
import enum

class TransactionType(str, enum.Enum):
    INCOME = "INCOME"   # Entrada (Ventas)
    EXPENSE = "EXPENSE" # Salida (Gastos, Nómina)
    
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    transactionType = Column(String, nullable=False)        # INCOME o EXPENSE
    category = Column(String, nullable=False)               # Ventas, Nómina, Alquiler
    amount = Column(Numeric(10, 2), nullable=False)         
    currency = Column(String(3), default="USD")
    
    description = Column(String, nullable=True)
    reference_id = Column(String, nullable=True)            # ID de factura o ID de pago de nómina
    
    created_at = Column(DateTime(timezone=True))