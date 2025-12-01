from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

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
    currency: str = "USD"
    items: List[InvoiceItemCreate] # Recibe una lista de items

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
    
    items: List[InvoiceItemResponse] # Devuelve el detalle}
    payments: List[PaymentResponse] = []
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