// Enum para Tipos de Cuenta
export type AccountType = 'ASSET' | 'LIABILITY' | 'EQUITY' | 'REVENUE' | 'EXPENSE';

// Modelo de Cuenta
export interface AccountCreate {
  code: string;
  name: string;
  account_type: string;
  parent_id?: number | null;
  is_transactional: boolean;
}

export interface AccountUpdate {
  name: string;
  is_active: boolean;
}

export interface Account {
  id: number;
  tenant_id: number;
  code: string;
  name: string;
  account_type: AccountType;
  level: number;
  is_transactional: boolean;
  parent_id?: number | null;
  balance: number;
  is_active: boolean;
}

// Modelos para Asientos
export interface LedgerLineCreate {
  account_id: number;
  debit: number;
  credit: number;
}

export interface LedgerEntryCreate {
  transaction_date: string; // YYYY-MM-DD
  description: string;
  reference?: string;
  lines: LedgerLineCreate[];
}

export interface LedgerEntryResponse extends LedgerEntryCreate {
  id: number;
  created_at: string;
  total_amount: number;
}

// Modelos para Plantillas 
export interface TemplateOption {
  label: string;
  value: string;
}

export interface TemplateField {
  key: string;
  label: string;
  type: 'number' | 'text' | 'select'; // Mapeo simple para inputs
  required: boolean;
  options?: TemplateOption[];
}

export interface EntryTemplate {
  id: string;
  name: string;
  description: string;
  fields: TemplateField[];
}

export interface ApplyTemplateRequest {
  template_id: string;
  data: Record<string, any>; // { "amount": 100, "concept": "X" }
}