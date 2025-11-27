from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True) # ID interno Global
    tenant_id = Column(Integer, index=True, nullable=False) # Empresa que creo la Factura
    
    # --- NUMERACIÓN FISCAL ---
    # Este número se reinicia para cada empresa
    invoice_number = Column(Integer, nullable=False)
    control_number = Column(String, nullable=True) # Opcional según formato
    
    # Datos fiscales Snapshot
    # Por si la empresa cambia de dirección mañana, la factura vieja no cambia
    company_name_snapshot = Column(String)
    company_rif_snapshot = Column(String)
    compant_address_snapshot = Column(String)
    
    # Cliente
    customer_name = Column(String)      # Nombre o Razón Social Cliente
    customer_rif = Column(String)       # RIF/Cédula Cliente
    customer_email = Column(String, index=True)
    customer_address = Column(String)
    
    # Datos de la Transacción
    amount = Column(Numeric(10, 2), nullable=True)  # Moneda siempre en Decimal/Numeric
    currency = Column(String(3), default="USD")     # USD, VES 
    exchange_rate = Column(Numeric(20, 6), nullable=True) # Tasa usada
    amount_ves = Column(Numeric(20, 2), nullable=True) # Contravalor en Bs.
    status = Column(String, default="DRAFT")        # DRAFT, SENT, PAID
    is_synced_compliance = Column(Boolean, default=False) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # CAMPOS FISCALES
    # Todos estos se guardan en la moneda base
    subtotal_exento = Column(Numeric(12, 2), default=0)     # Monto no gravado
    subtotal_base_g = Column(Numeric(12, 2), default=0)     # Base Imponible Alícuota General (16%)
    subtotal_base_r = Column(Numeric(12, 2), default=0)     # Base Imponible Alícuota Reducida (ej. 8%)
    subtotal_base_a = Column(Numeric(12, 2), default=0)     # Base Imponible Alícuota Adicional (lujo)
    
    tax_g = Column(Numeric(12, 2), default=0)               # IVA 16% calculado
    tax_r = Column(Numeric(12, 2), default=0)               # IVA reducido calculado
    tax_a = Column(Numeric(12, 2), default=0)               # IVA adicional calculado
    
    total_amount = Column(Numeric(12, 2), nullable=False)   # Suma de todo lo anterior
    
    rate = Column(Numeric(12, 2), nullable=False)           # Tasa BCV del momento exacto de la venta
    
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