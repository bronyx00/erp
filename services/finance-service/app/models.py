from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_email = Column(String, index=True, nullable=False) # Quien creo la factura
    customer_email = Column(String, index=True) # Email del cliente
    
    # Datos de la Transacción
    amount = Column(Numeric(10, 2), nullable=True)  # Moneda siempre en Decimal/Numeric
    currency = Column(String(3), default="USD")     # USD, VES 
    exchange_rate = Column(Numeric(20, 6), nullable=True) # Tasa usada
    amount_ves = Column(Numeric(20, 2), nullable=True) # Contravalor en Bs.
    status = Column(String, default="DRAFT")        # DRAFT, SENT, PAID
    is_synced_compliance = Column(Boolean, default=False) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    items = relationship("InvoiceItem", back_populates="invoice")
    payments = relationship("Payment", back_populates="invoice")
    
class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    
    product_id = Column(Integer, nullable=False) # ID del producto en Inventary Service
    product_name = Column(String) # Guarda el nombre por si cambia en el futuro
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(10, 2)) # Precio al momento de la venta
    total_price = Column(Numeric(10, 2)) # qty * unit_price
    
    invoice = relationship("Invoice", back_populates="items")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    
    amount = Column(Numeric(10, 2), nullable=False) # Monto pagado
    currency = Column(String(3), default="USD")     # Moneda del pago
    payment_method = Column(String)
    reference = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    invoice = relationship("Invoice", back_populates="payments")

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    currency_from = Column(String(3), default="USD")    # De qué moneda (Dólar)
    currency_to = Column(String(3), default="VES")      # A qué moneda (Bs)
    rate = Column(Numeric(20, 6), nullable=False)       # Tasa (ej. 36.543210)
    source = Column(String, default="BCV")              # Fuente (BCV)
    acquired_at = Column(DateTime(timezone=True), server_default=func.now()) # Cuándo la guardamos