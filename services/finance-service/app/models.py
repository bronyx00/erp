from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class FinanceSettings(Base):
    """
    Configuración global del módulo de Finanzas por empresa (Tenant).
    Define moneda base, impuestos y reglas de facturación.
    """
    __tablename__ = "finance_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    enable_salesperson_selection = Column(Boolean, default=False)
    default_currency = Column(String, default="USD")
    tax_rate = Column(Numeric(5, 2), default=16.00) # IVA por defecto
    

class Invoice(Base):
    """
    Cabecera de Factura.
    Representa una venta fiscal o interna.
    """
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)              # ID interno Global
    tenant_id = Column(Integer, index=True, nullable=False)         # Empresa que creo la Factura
    salesperson_id = Column(Integer, nullable=True, index=True)     # ID de empleado quien hizo la venta
    created_by_user_id = Column(Integer, nullable=False)            # El usuario que registró la factura
    
    # --- NUMERACIÓN FISCAL ---
    # Este número se reinicia para cada empresa
    invoice_number = Column(Integer, nullable=False)                # Consecutivo (ej. 148988)
    control_number = Column(String, nullable=True)                  # Serie 00-XXXX
    
    # Datos fiscales Snapshot
    # Por si la empresa cambia de dirección mañana, la factura vieja no cambia
    company_name = Column(String)
    company_rif = Column(String)
    company_address = Column(String)
    
    # Cliente
    customer_name = Column(String)                                  # Nombre o Razón Social Cliente
    customer_rif = Column(String)                                   # RIF/Cédula Cliente
    customer_email = Column(String, index=True)
    customer_address = Column(String)
    customer_phone = Column(String)

    # ---- MONTOS ----
    # Base Imponible y Exento
    subtotal_usd = Column(Numeric(12, 2), default=0)
    tax_amount_usd = Column(Numeric(12, 2), default=0)
    total_usd = Column(Numeric(12, 2), nullable=False)
    
    # Conversión BCV
    currency = Column(String(3), default="USD")                     # USD, VES 
    exchange_rate = Column(Numeric(12, 4), nullable=True)           # Tasa usada
    amount_ves = Column(Numeric(20, 2), nullable=True)              # Contravalor en Bs.
    
    status = Column(String, default="ISSUED")                       # ISSUED, PAID, VOID
    is_synced_compliance = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    issue_date = Column(Date, nullable=False)
    
    # --- AUDITORIA ---
    created_by_role = Column(String, nullable=True)                 # Rol al momento de crear
    
    # Relaciones
    items = relationship("InvoiceItem", back_populates="invoice")
    payments = relationship("Payment", back_populates="invoice")
    
class InvoiceItem(Base):
    """Detalle de productos o servicios dentro de una factura."""
    __tablename__ = "invoice_items"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    
    product_id = Column(Integer, nullable=False)                    # ID del producto en Inventary Service
    product_name = Column(String)                                   # Guarda el nombre por si cambia en el futuro
    quantity = Column(Numeric(12, 3), default=1)
    unit_price = Column(Numeric(10, 2))                             # Precio al momento de la venta
    total_price = Column(Numeric(10, 2))                            # qty * unit_price
    
    invoice = relationship("Invoice", back_populates="items")

class Payment(Base):
    """Registro de pagos recibidos asociados a una factura."""
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
    """Histórico de tasas de cambio (BCV/Paralelo)."""
    __tablename__ = "exchange_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    currency_from = Column(String(3), default="USD")    # De qué moneda (Dólar)
    currency_to = Column(String(3), default="VES")      # A qué moneda (Bs)
    rate = Column(Numeric(20, 6), nullable=False)       # Tasa (ej. 36.543210)
    source = Column(String, default="BCV")              # Fuente (BCV)
    acquired_at = Column(DateTime(timezone=True), server_default=func.now()) # Cuándo la guardamos
    
class Quote(Base):
    """Cotizaciones / Presupuestos."""
    __tablename__ = "quotes"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True, nullable=False)
    
    # Datos de Control
    quote_number = Column(String, index=True)   # Ej: COT-0001
    status = Column(String, default="DRAFT")    # DRAFT, SENT, ACCEPTED, REJECTED, INVOICED
    
    # Cliente (Snapshot para historial)
    customer_id = Column(Integer, nullable=True)
    customer_name = Column(String)
    customer_rif = Column(String)
    customer_email = Column(String, nullable=True)
    customer_address = Column(Text, nullable=True)
    customer_phone = Column(String, nullable=True)
    
    # Fechas
    date_issued = Column(Date, nullable=False)
    date_expires = Column(Date, nullable=False)
    
    # Montos
    currency = Column(String, default="USD")
    subtotal = Column(Numeric(12, 2), default=0)
    tax_amount = Column(Numeric(12, 2), default=0)
    total = Column(Numeric(12, 2), default=0)
    
    notes = Column(Text, nullable=True)
    terms = Column(Text, nullable=True) # Términos y condiciones
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_email = Column(String, nullable=True) # Firma
    
    # Relaciones
    items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan")
    
class QuoteItem(Base):
    """Items de una cotización."""
    __tablename__ = "quote_items"
    
    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(Integer, ForeignKey("quotes.id"))
    
    product_id = Column(Integer)
    product_name = Column(String)
    description = Column(String, nullable=True)
    
    quantity = Column(Numeric(12, 3), default=1)
    unit_price = Column(Numeric(12, 2))
    total_price = Column(Numeric(12, 2))
    
    quote = relationship("Quote", back_populates="items")