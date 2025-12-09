from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List

class AccountBase(BaseModel):
    code: str
    name: str
    account_type: str   # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE, ORDER
    level: int = 1
    is_transactional: bool = True
    parent_id: Optional[str] = None
    description: Optional[str] = None
    
class AccountCreate(AccountBase):
    initial_balance: Decimal = Decimal(0)
    
class AccountResponse(AccountBase):
    id: int
    tenant_id: int
    balance: Decimal
    is_active: bool
    model_config = ConfigDict(from_attributes=True)
    
# --- IMPORT RESPONSE ---
class ImportResult(BaseModel):
    total_processed: int
    message: str
    
# --- LEDGER SCHEMAS ---
class LedgerLineResponse(BaseModel):
    account_id: int
    account_name: str = Field(validation_alias="account.name") 
    code: str = Field(validation_alias="account.code")
    debit: Decimal
    credit: Decimal
    model_config = ConfigDict(from_attributes=True)
    
class LedgerEntryResponse(BaseModel):
    id: int
    transaction_date: date
    description: str
    reference: Optional[str]
    total_amount: Decimal
    lines: List[LedgerLineResponse] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

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