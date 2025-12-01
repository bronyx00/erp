import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Customer {
  id?: number;
  name: string;
  email: string;
  tax_id?: string;
  phone?: string;
  address?: string;
  is_active?: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class CrmService {
  private http = inject(HttpClient);
  private readonly API_URL = 'http://localhost:80/api/crm';

  getCustomers(): Observable<Customer[]> {
    return this.http.get<Customer[]>(`${this.API_URL}/customers`);
  }

  createCustomer(customer: Customer): Observable<Customer> {
    return this.http.post<Customer>(`${this.API_URL}/customers`, customer);
  }
}
