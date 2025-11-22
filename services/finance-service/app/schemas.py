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
    customer_email: str
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
    status: str
    amount: Decimal # Total calculado
    currency: str
    items: List[InvoiceItemResponse] # Devuelve el detalle}
    
    payments: List[PaymentResponse] = []
    
    created_at: datetime
    
    exchange_rate: Optional[Decimal] = None
    amount_ves: Optional[Decimal] = None
    
    model_config = ConfigDict(from_attributes=True)