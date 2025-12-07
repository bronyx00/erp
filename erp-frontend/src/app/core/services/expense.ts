import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';

export type ExpenseStatus = 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'PAID' | 'REFUSED';

export interface Expense {
  id: number;
  date: string;
  description: string;
  category: string; 
  amount: number;
  tax_amount: number;
  total_amount: number;
  currency: string;
  employee_name: string;
  receipt_url?: string; // Imagen del recibo
  status: ExpenseStatus;

  is_billable: boolean; // ¿Se cobra al cliente? (Ventas)
  customer_name?: string; // Cliente a cobrar
  accounting_account?: string; // Cuenta contable
}

export interface ExpenseReportStats {
  to_submit: number;
  to_approve: number;
  to_pay: number;
}

const MOCK_EXPENSES: Expense[] = [
  { id: 1, date: '2025-12-05', description: 'Almuerzo con Cliente', category: 'Comidas', amount: 45.00, tax_amount: 0, total_amount: 45.00, currency: 'USD', employee_name: 'Ana García', status: 'DRAFT', is_billable: true, customer_name: 'Tecno Soluciones', accounting_account: '6201 - Atenciones' },
  { id: 2, date: '2025-12-04', description: 'Vuelo a Conferencia', category: 'Viajes', amount: 350.00, tax_amount: 0, total_amount: 350.00, currency: 'USD', employee_name: 'Ana García', status: 'SUBMITTED', is_billable: false, accounting_account: '6202 - Pasajes' },
  { id: 3, date: '2025-12-01', description: 'Licencia Software Diseño', category: 'Oficina', amount: 120.00, tax_amount: 19.20, total_amount: 139.20, currency: 'USD', employee_name: 'Ana García', status: 'APPROVED', is_billable: false, accounting_account: '6205 - Software' },
  { id: 4, date: '2025-11-28', description: 'Uber a Aeropuerto', category: 'Transporte', amount: 25.00, tax_amount: 0, total_amount: 25.00, currency: 'USD', employee_name: 'Ana García', status: 'PAID', is_billable: true, customer_name: 'Distribuidora Global', accounting_account: '6203 - Transporte' },
];

@Injectable({
  providedIn: 'root',
})
export class ExpenseService {
  getExpenses(): Observable<Expense[]> {
    return of(MOCK_EXPENSES);
  }

  getStats(): Observable<ExpenseReportStats> {
    return of({ to_submit: 45.00, to_approve: 350.00, to_pay: 139.20 })
  }

  createExpense(expense: Expense, status: ExpenseStatus = 'DRAFT'): Observable<Expense> {
    const newExpense = { ...expense, id: Date.now(), date: Date.now().toString(), status: status }

    MOCK_EXPENSES.unshift(newExpense);
    return of(newExpense);
  }
}
