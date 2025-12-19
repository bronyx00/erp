from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from datetime import datetime, date
from typing import List, Optional, Generic, TypeVar

T = TypeVar("T")

# --- GENERIC PAGINATOR ---
class MetaData(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    
class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: MetaData
    
# --- SETTINGS SCHEMAS ---
class FinanceSettingsBase(BaseModel):
    enable_salesperson_selection: bool = False
    default_currency: str = "USD"
    
class FinanceSettingsRead(FinanceSettingsBase):
    id: int
    tenant_id: int
    
    model_config = ConfigDict(from_attributes=True)
    
# --- INVOICE SUMMARY (Ligera) ---
class InvoiceSummary(BaseModel):
    id: int
    invoice_number: int
    control_number: Optional[str] = None
    status: str
    total_usd: Decimal
    salesperson_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_rif: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
class InvoicePaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Monto del abono o pago total")
    payment_method: str = Field(..., description="CASH, TTDB, PAGO_MOVIL, TRANSFER")
    reference: Optional[str] = Field(None, description="Referencia bancaria")
    notes: Optional[str] = None    

# --- INVOICE SCHEMAS ---
class InvoiceItemCreate(BaseModel):
    product_id: int
    quantity: int
    
class InvoiceItemResponse(BaseModel):
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    model_config = ConfigDict(from_attributes=True)

class InvoiceCreate(BaseModel):
    customer_tax_id: str
    salesperson_id: Optional[int] = None
    currency: str = "USD"
    items: List[InvoiceItemCreate] = Field(..., min_items=1, description="Lista de productos a facturar")
    payment: Optional[InvoicePaymentCreate] = Field(None, description="Datos del pago inicial (si existe)")

class PaymentCreate(BaseModel):
    invoice_id: int
    amount: Decimal
    payment_method: str # Zelle, Cash, Transferencia
    reference: Optional[str] = None
    notes: Optional[str] = None
    
class PaymentResponse(BaseModel):
    id: int
    amount: Decimal
    payment_method: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class InvoiceResponse(BaseModel):
    id: int
    invoice_number: int
    control_number: Optional[str] = None
    status: str
    
    subtotal_usd: Decimal
    tax_amount_usd: Decimal
    total_usd: Decimal
    
    currency: str
    exchange_rate: Optional[Decimal] = None
    amount_ves: Optional[Decimal] = None
    
    # Datos Cliente
    customer_name: Optional[str] = None
    customer_rif: Optional[str] = None
    customer_email: Optional[str] = None
    
    salesperson_id: Optional[int] = None
    
    items: List[InvoiceItemResponse] # Devuelve el detalle}
    payments: List[PaymentResponse] = []
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
# --- Cotizaciones ---
class QuoteItemCreate(BaseModel):
    product_id: int
    quantity: int = 1
    # Permite sobreescribir precio o descripción
    unit_price: Optional[Decimal] = None
    description: Optional[str] = None
    
class QuoteCreate(BaseModel):
    customer_tax_id: str    # Para buscar en CRM
    date_expires: date
    currency: str = "USD"
    items: List[QuoteItemCreate]
    notes: Optional[str] = None
    terms: Optional[str] = None
    
class QuoteItemResponse(BaseModel):
    id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    model_config = ConfigDict(from_attributes=True)
    
class QuoteResponse(BaseModel):
    id: int
    quote_number: str
    status: str
    customer_name: str
    date_issued: date
    date_expires: date
    total: Decimal
    currency: str
    items: List[QuoteItemResponse]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- REPORTES ---
class DailySales(BaseModel):
    date: datetime
    total_sales: Decimal
    invoice_count: int

class DashboardMetrics(BaseModel):
    today_sales: Decimal
    month_sales: Decimal
    pending_balance: Decimal # Cuentas por cobrar
    total_invoices_today: int
    
class SalesReportItem(BaseModel):
    date: datetime
    payment_method: str
    currency: str
    total_amount: Decimal
    transaction_count: int
    
class SalesReportResponse(BaseModel):
    items: List[SalesReportItem]
    
class SalesDataPoint(BaseModel):
    month: str
    sales_usd: float
    
# --- REPORTE DE COMISIONES ---
class SalesTotalResponse(BaseModel):
    tenant_id: int
    employee_id: int
    total_sales_usd: Decimal
    period_start: date
    period_end: date