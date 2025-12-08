import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Transaction {
  id: number;
  transaction_type: 'INCOME' | 'EXPENSE';
  category: string;
  amount: number;
  description: string;
  created_at: string;
}

export interface Balance {
  total_income: number;
  total_expense: number;
  net_profit: string;
}

@Injectable({
  providedIn: 'root',
})
export class AccountingService {
  private http = inject(HttpClient);
  private readonly API_URL = `${environment}/accounting`;

  // Crear transacción manual
  createTransaction(data: any): Observable<Transaction> {
    return this.http.post<Transaction>(`${this.API_URL}/transactions`, data);
  }

  getBalance(): Observable<Balance> {
    return this.http.get<Balance>(`${this.API_URL}/balance`);
  }
}
