from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List, Generic, TypeVar

T = TypeVar("T")

class MetaData(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: MetaData

class SeedPucRequest(BaseModel):
    sector: str = "commerce" # Valores: 'commerce', 'services', 'industry', 'agriculture'

# --- ACCOUNT MANAGEMENT ---
class AccountBase(BaseModel):
    code: str
    name: str
    account_type: str   # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE, ORDER
    level: int = 1
    is_transactional: bool = True
    parent_id: Optional[int] = None
    description: Optional[str] = None
    
class AccountCreate(AccountBase):
    code: str
    name: str
    parent_id: Optional[int] = None
    account_type: str # ASSET, LIABILITY, etc.
    is_transactional: bool = True
    
class AccountUpdate(BaseModel):
    name: str
    is_active: bool = True
    
class AccountResponse(AccountBase):
    id: int
    tenant_id: int
    balance: Decimal
    is_active: bool
    parent_id: Optional[int]
    model_config = ConfigDict(from_attributes=True)
    
# --- IMPORT RESPONSE ---
class ImportResult(BaseModel):
    total_processed: int
    message: str
    
# --- LEDGER SCHEMAS ---

# Sub-esquema para la cuenta anidada
class AccountSimpleResponse(BaseModel):
    name: Optional[str] = "Desconocida"
    code: Optional[str] = "000"
    model_config = ConfigDict(from_attributes=True)

class LedgerLineCreate(BaseModel):
    account_id: int
    debit: Decimal = Decimal(0)
    credit: Decimal = Decimal(0)

    # Validacion basica
    def validate_positive(self):
        if self.debit < 0 or self.credit < 0:
            raise ValueError("Los montos no pueden ser negativos")
        
class LedgerLineResponse(BaseModel):
    account_id: int
    account: Optional[AccountSimpleResponse] = None
    debit: Decimal
    credit: Decimal
    model_config = ConfigDict(from_attributes=True)
    
class LedgerEntryCreate(BaseModel):
    transaction_date: date
    description: str
    reference: Optional[str] = None
    lines: List[LedgerLineCreate]

    @property
    def total_debit(self) -> Decimal:
        return sum(line.debit for line in self.lines)

    @property
    def total_credit(self) -> Decimal:
        return sum(line.credit for line in self.lines)
    
    @property
    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit
    
class LedgerEntryResponse(BaseModel):
    id: int
    transaction_date: date
    description: str
    reference: Optional[str]
    total_amount: Decimal
    lines: List[LedgerLineResponse] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
    
# --- TEMPLATE SCHEMAS ---
class TemplateOption(BaseModel):
    label: str          # Nombre para usuario
    value: str          # Nombre para DB

class TemplateField(BaseModel):
    key: str            # 'amount', 'provider_name', 'payment_method'
    label: str          # 'Monto Total', 'Nombre Proveedor'
    type: str           # 'number', 'text', 'select'
    required: bool = True
    options: Optional[List[TemplateOption]] = None

class EntryTemplate(BaseModel):
    id: str             # 'expense_general'
    name: str           # 'Registrar Gasto General'
    description: str    # 'Gastos de papelería, limpieza, etc.'
    fields: List[TemplateField]

class ApplyTemplateRequest(BaseModel):
    template_id: str
    data: dict          # { "amount": 100, "notes": "Compra toners" }
    

class TransactionBase(BaseModel):
    transaction_type: str # INCOME / EXPENSE
    category: str
    amount: Decimal
    currency: str = "USD"
    description: Optional[str] = None
    reference_id: Optional[str] = None
    
class TransactionCreate(TransactionBase):
    created_at: Optional[datetime] = None
    pass

class TransactionResponse(TransactionBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
    
class BalanceResponse(BaseModel):
    total_income: Decimal
    total_expense: Decimal
    net_profit: Decimal