import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { environment } from '../../../environments/environment';

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
  address?: string;

  bonus_scheme?: string;
  birth_date?: string;
  performace_reviews?: Array<{
    date: string;
    rating: number;
    summary: string;
  }>;
  emergency_contact?: any;
  documents: any[];
  manager_name?: string;
  status: 'Active' | 'On Leave' | 'Terminated';
}

const MOCK_EMPLOYEE: Employee = {
    id: 101,
    first_name: 'Ana',
    last_name: 'García Reyes',
    position: 'MANAGER',
    email: 'ana.garcia@erpcorp.com',
    phone: '0412-555-1234',
    hired_at: '2018-03-15',
    is_active: true,
    status: 'Active',
    salary: 3500.00,
    bonus_scheme: '3% sobre ventas',
    identification: 'V-15.456.789',
    address: 'Av. Principal, Edif. Apto 4A, Caracas, Venezuela',
    birth_date: '1985-11-20',
    manager_name: 'Leonel Gonzalez',
    emergency_contact: {
        name: 'José García',
        phone: '+58 414-555-9876',
        relationship: 'Hermano',
    },
    performace_reviews: [
        { date: '2024-01-20', rating: 5, summary: 'Desempeño sobresaliente, superó todas las metas de Q4.' },
        { date: '2023-07-15', rating: 4, summary: 'Buen progreso, requiere enfoque en desarrollo de nuevos clientes.' },
    ],
    documents: [
        { name: 'Contrato Laboral Inicial', type: 'PDF', uploaded_date: '2018-03-10', url: '#' },
        { name: 'Certificado de Cursos', type: 'PDF', uploaded_date: '2022-09-01', url: '#' },
        { name: 'Documento de Identidad', type: 'JPG', uploaded_date: '2023-05-01', url: '#' },
    ]
};

@Injectable({
  providedIn: 'root',
})
export class HhrrService {
  private http = inject(HttpClient);
  private readonly API_URL = `${environment.apiUrl}/hhrr`;

  getEmployees(): Observable<Employee[]> {
    return this.http.get<Employee[]>(`${this.API_URL}/employees`);
  }

  getEmployeeById(id: number): Observable<Employee> {
    return this.http.get<Employee>(`${this.API_URL}/employees/${id}`);
  }

  getEmployeeDetail(id: number): Observable<Employee | undefined> {
    return this.getEmployeeById(id);
  }

  createEmployee(employee: Employee): Observable<Employee> {
    return this.http.post<Employee>(`${this.API_URL}/employees`, employee);
  }
}
