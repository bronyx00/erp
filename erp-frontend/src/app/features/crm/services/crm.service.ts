import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { map, Observable, tap, finalize } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Customer, CustomerPayload, PaginatedResult } from '../models/customer.model';

@Injectable({ providedIn: 'root' })
export class CrmService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/crm/customers`; 

  // --- STATE SIGNALS (Gestión de estado local del servicio) ---
  // Esto permite que cualquier componente sepa si estamos cargando data
  isLoading = signal<boolean>(false);

  /**
   * Obtiene clientes con paginación y transforma snake_case -> camelCase
   */
  getCustomers(page: number = 1, limit: number = 10, search: string = ''): Observable<PaginatedResult<Customer>> {
    this.isLoading.set(true);
    
    let params = new HttpParams()
      .set('page', page)
      .set('limit', limit);
      
    if (search) params = params.set('search', search);

    return this.http.get<any>(this.apiUrl, { params }).pipe(
      map(response => ({
        data: response.data.map((item: any) => this.adaptToFrontend(item)),
        meta: {
          total: response.meta.total,
          page: response.meta.page,
          limit: response.meta.limit,
          totalPages: response.meta.total_pages
        }
      })),
      finalize(() => this.isLoading.set(false))
    );
  }

  /**
   * Crea un cliente nuevo 
   */
  createCustomer(payload: CustomerPayload): Observable<Customer> {
    this.isLoading.set(true);
    // Convertimos a snake_case para el backend
    const apiPayload = {
      ...payload,
      tax_id: payload.tax_id, // Asegurarnos que coincida con schema Pydantic
    };
    return this.http.post<any>(this.apiUrl, apiPayload).pipe(
      map(item => this.adaptToFrontend(item)),
      finalize(() => this.isLoading.set(false))
    );
  }

  /**
   * Actualiza un cliente existente
   */
  updateCustomer(id: number, payload: CustomerPayload): Observable<Customer> {
    this.isLoading.set(true);
    // Aseguramos consistencia de datos para Python
    const apiPayload = {
      ...payload,
      tax_id: payload.tax_id, 
    };

    return this.http.put<any>(`${this.apiUrl}/${id}`, apiPayload).pipe(
      map(item => this.adaptToFrontend(item)),
      finalize(() => this.isLoading.set(false))
    );
  }

  // --- ADAPTER (The Bridge) ---
  private adaptToFrontend(data: any): Customer {
    return {
      id: data.id,
      name: data.name,
      email: data.email,
      taxId: data.tax_id,
      phone: data.phone,
      address: data.address,
      isActive: data.is_active,
      createdAt: data.created_at,
      avatarInitials: data.name.substring(0, 2).toUpperCase()
    };
  }
}