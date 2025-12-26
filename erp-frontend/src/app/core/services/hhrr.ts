import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface EmergencyContact {
  name: string;
  phone: string;
  relationship: string;
}

export interface SupervisorNote {
  id: number;
  employee_id: number;
  supervisor_email: string;
  category: string;
  content: string;
  is_private: boolean;
  created_at: string;
}

export interface SupervisorNoteCreate {
  employee_id: number;
  category: string;
  content: string;
  is_private: boolean;
}

export interface EmployeeBase {
  first_name: string;
  last_name: string;
  identification: string;
  email: string;
  phone?: string;
  address?: string;
  birth_date?: string;
  position: string;
  department: string;
  hired_at: string;
  schedule_id?: number | null;
  contract_type?: string;
  salary: number | string;
  bonus_scheme?: string;
  emergency_contact: EmergencyContact;
  documents?: any[];
  performance_reviews?: any[];
  is_active: boolean;
  status?: string;
}

export interface Employee extends EmployeeBase {
  id: number;
  created_at: string;
  manager_id?: number | null;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: any;
}

export interface EmployeeResponse {
  data: Employee[];
  meta: any;
}

export interface WorkSchedule {
  id: number;
  name: string;
  is_active: boolean;
  // Horas (pueden ser null si es dia libre)
  monday_start?: string; monday_end?: string;
  tuesday_start?: string; tuesday_end?: string;
  wednesday_start?: string; wednesday_end?: string;
  thursday_start?: string; thursday_end?: string;
  friday_start?: string; friday_end?: string;
  saturday_start?: string; saturday_end?: string;
  sunday_start?: string; sunday_end?: string;
}

// --- HORARIOS ---
export interface WorkScheduleCreate {
  name: string;
  monday_start?: string | null; monday_end?: string | null;
  tuesday_start?: string | null; tuesday_end?: string | null;
  wednesday_start?: string | null; wednesday_end?: string | null;
  thursday_start?: string | null; thursday_end?: string | null;
  friday_start?: string | null; friday_end?: string | null;
  saturday_start?: string | null; saturday_end?: string | null;
  sunday_start?: string | null; sunday_end?: string | null;
}

export interface Payroll {
  id: number;
  employee_id: number;
  period_start: string;
  period_end: string;
  base_salary: number;
  bonuses: number;
  deductions: number;
  net_salary: number;
  status: 'DRAFT' | 'APPROVED' | 'PAID';
  payment_date?: string;
  employee?: Employee; // Si el backend hace join
}

export interface PayrollGenerateParams {
  period_start: string;
  period_end: string;
}

@Injectable({
  providedIn: 'root'
})
export class HhrrService {
  private http = inject(HttpClient);
  // Asumiendo que el servicio corre en /hhrr o similar según tu gateway
  private readonly API_URL = `${environment.apiUrl}/hhrr`; 

  // --- EMPLEADOS ---
  getEmployees(skip: number = 0, limit: number = 100, search?: string): Observable<EmployeeResponse> {
    let params = new HttpParams().set('page', '1').set('limit', limit);
    
    if (search) params = params.set('q', search); 

    // Retornamos el objeto completo (data + meta)
    return this.http.get<EmployeeResponse>(`${this.API_URL}/employees`, { params });
  }

  getEmployeeById(id: number): Observable<Employee> {
    return this.http.get<Employee>(`${this.API_URL}/employees/${id}`);
  }

  getEmployeeDetail(id: number): Observable<Employee | undefined> {
    return this.getEmployeeById(id);
  }

  createEmployee(employee: EmployeeBase): Observable<Employee> {
    return this.http.post<Employee>(`${this.API_URL}/employees`, employee);
  }

  updateEmployee(id: number, data: Partial<EmployeeBase>): Observable<Employee> {
    return this.http.put<Employee>(`${this.API_URL}/employees/${id}`, data);
  }

  // --- NOTAS ---
  createNote(note: SupervisorNoteCreate): Observable<SupervisorNote> {
    return this.http.post<SupervisorNote>(`${this.API_URL}/notes`, note);
  }

  getEmployeeNotes(employeeId: number): Observable<PaginatedResponse<SupervisorNote>> {
    return this.http.get<PaginatedResponse<SupervisorNote>>(`${this.API_URL}/employees/${employeeId}/notes`);
  }

  // --- HORARIOS ---
  getSchedules(): Observable<WorkSchedule[]> {
    return this.http.get<WorkSchedule[]>(`${this.API_URL}/work-schedules`);
  }

  createSchedule(data: WorkScheduleCreate): Observable<WorkSchedule> {
    return this.http.post<WorkSchedule>(`${this.API_URL}/work-schedules`, data);
  }

  // --- NÓMINA ---

  generatePayroll(params: PayrollGenerateParams): Observable<Payroll[]> {
    return this.http.post<Payroll[]>(`${this.API_URL}/payrolls/generate`, params);
  }

  getPayrolls(skip: number = 0, limit: number = 100): Observable<Payroll[]> {
    return this.http.get<Payroll[]>(`${this.API_URL}/payrolls/`, {
      params: { skip, limit }
    });
  }

  approvePayroll(id: number): Observable<Payroll> {
    return this.http.post<Payroll>(`${this.API_URL}/payrolls/${id}/approve`, {});
  }
  
  payPayroll(id: number): Observable<Payroll> {
    return this.http.post<Payroll>(`${this.API_URL}/payrolls/${id}/pay`, {});
  }
}