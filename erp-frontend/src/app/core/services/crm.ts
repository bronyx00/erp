import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Customer {
  id: number;
  name: string;
  email: string;
  tax_id?: string;
  phone: string;
  address?: string;
  is_active?: boolean;
  total_puchases?: number;
  last_puchase_date?: Date;
  puchases_history?: any[];
}

@Injectable({
  providedIn: 'root',
})
export class CrmService {
  private http = inject(HttpClient);
  private readonly API_URL = `${environment.apiUrl}/crm`;

  getCustomers(): Observable<Customer[]> {
    return this.http.get<Customer[]>(`${this.API_URL}/customers`);
  }

  createCustomer(customer: Customer): Observable<Customer> {
    return this.http.post<Customer>(`${this.API_URL}/customers`, customer);
  }
}
