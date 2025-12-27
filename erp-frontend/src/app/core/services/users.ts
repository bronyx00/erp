import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../../environments/environment';
import { HhrrService } from './hhrr';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'OWNER' | 'ADMIN' | 'SALES_AGENT' | 'SALES_SUPERVISOR' | 'ACCOUNTANT' | 'WAREHOUSE_CLERK' | 'WAREHOUSE_SUPERVISOR' | 'RRHH_MANAGER' | 'PROJECT_MANAGER';
  is_active: boolean;
  tenant_id: number;
  last_login?: string;
}

export interface CreateUserDto {
  full_name: string;
  email: string;
  password: string;
  role: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: {
    total: number;
    page: number;
    limit: number;
    total_pages: number;
  };
}

@Injectable({
  providedIn: 'root'
})
export class UsersService {
  private http = inject(HttpClient);
  private hhrrService = inject(HhrrService); // Para buscar empleados disponibles
  
  // Apunta a tu Auth Service
  private readonly API_URL = `${environment.apiUrl}/auth`; 

  getUsers(page: number = 1, limit: number = 10, search: string = ''): Observable<PaginatedResponse<User>> {
    let params = new HttpParams()
      .set('page', page)
      .set('limit', limit);
    
    if (search) params = params.set('search', search);

    return this.http.get<PaginatedResponse<User>>(`${this.API_URL}/users`, { params });
  }

  createUser(user: CreateUserDto): Observable<User> {
    return this.http.post<User>(`${this.API_URL}/users`, user);
  }

  // --- Helpers de UI ---
  
  // Obtiene empleados de RRHH para el dropdown de "Vincular Usuario"
  getEmployeesForLinking(): Observable<any[]> {
    // Pedimos una lista grande para filtrar en el select (idealmente tendrías un endpoint dedicado 'available')
    return this.hhrrService.getEmployees(1, 100).pipe(
      map(res => res.data.filter((e: any) => e.is_active))
    );
  }
}