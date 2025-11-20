from pydantic import BaseModel, ConfigDict
from decimal import Decimal

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
    
    model_config = ConfigDict(from_attributes=True)