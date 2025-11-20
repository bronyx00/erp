from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_email = Column(String, index=True)
    amount = Column(Numeric(10, 2), nullable=True)  # Moneda siempre en Decimal/Numeric
    currency = Column(String(3), default="USD")     # USD, VES 
    status = Column(String, default="DRAFT")        # DRAFT, SENT, PAID
    is_synced_compliance = Column(Boolean, default=False) # ¿Ya se envió a impuestos?
    
class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    currency_from = Column(String(3), default="USD")    # De qué moneda (Dólar)
    currency_to = Column(String(3), default="VES")      # A qué moneda (Bs)
    rate = Column(Numeric(20, 6), nullable=False)       # Tasa (ej. 36.543210)
    source = Column(String, default="BCV")              # Fuente (BCV)
    acquired_at = Column(DateTime(timezone=True), server_default=func.now()) # Cuándo la guardamos