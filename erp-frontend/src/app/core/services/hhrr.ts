import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Employee {
  id?: number;
  first_name: string;
  last_name: string;
  identification: string;
  email?: string;
  phone?: string;
  position?: string;
  salary: number;
  hired_at?: string;
  is_active?: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class HhrrService {
  private http = inject(HttpClient);
  private readonly API_URL = 'http://localhost:80/api/hhrr';

  getEmployees(): Observable<Employee[]> {
    return this.http.get<Employee[]>(`${this.API_URL}/employees`);
  }

  createEmployee(employee: Employee): Observable<Employee> {
    return this.http.post<Employee>(`${this.API_URL}/employees`, employee);
  }

  getEmployeeById(id: number): Observable<Employee> {
    return this.http.get<Employee>(`${this.API_URL}/employees/${id}`);
  }
}
