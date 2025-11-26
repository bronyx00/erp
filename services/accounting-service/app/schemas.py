from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import Optional

class TransactionBase(BaseModel):
    transaction_type: str # INCOME / EXPENSE
    category: str
    amount: Decimal
    currency: str = "USD"
    description: Optional[str] = None
    reference_id: Optional[str] = None
    
class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
    
class BalanceResponse(BaseModel):
    total_income: Decimal
    total_expense: Decimal
    net_profit: Decimal