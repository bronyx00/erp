from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import Optional

class InvoiceBase(BaseModel):
    customer_email: str
    amount: Decimal
    currency: str = "USD"
    
class InvoiceCreate(InvoiceBase):
    pass

class InvoiceResponse(InvoiceBase):
    id: int
    status: str
    is_synced_compliance: bool
    created_at = datetime
    
    exchange_rate = Optional[Decimal] = None
    amount_ves = Optional[Decimal] = None
    
    model_config = ConfigDict(from_attributes=True)