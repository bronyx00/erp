import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { map, Observable, finalize } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Product, ProductPayload, PaginatedProductResult } from '../models/product.model';

@Injectable({ providedIn: 'root' })
export class InventoryService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/inventory/products`;

  isLoading = signal(false);

  getProducts(page: number = 1, limit: number = 10, search: string = ''): Observable<PaginatedProductResult> {
    this.isLoading.set(true);
    let params = new HttpParams().set('page', page).set('limit', limit);
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
   * Obtiene las categorías activas en la base de datos.
   * NOTA: Esto debería ser un endpoint real del backend.
   * Por ahora, haremos una llamada simulada o extraeremos de productos (subóptimo pero funcional).
   */
  getCategories(): Observable<string[]> {
    // Ideal: return this.http.get<string[]>(`${this.apiUrl}/categories`);
    
    // Fallback Frontend (Temporal hasta que backend implemente endpoint):
    // Pedimos 100 productos y extraemos categorías únicas
    return this.getProducts(1, 100).pipe(
        map(res => {
            const cats = new Set(res.data.map(p => p.category));
            return ['Todas', ...Array.from(cats).sort()];
        })
    );
  }

  createProduct(payload: ProductPayload): Observable<Product> {
    this.isLoading.set(true);
    return this.http.post<any>(this.apiUrl, payload).pipe(
      map(item => this.adaptToFrontend(item)),
      finalize(() => this.isLoading.set(false))
    );
  }

  updateProduct(id: number, payload: ProductPayload): Observable<Product> {
    this.isLoading.set(true);
    return this.http.put<any>(`${this.apiUrl}/${id}`, payload).pipe(
      map(item => this.adaptToFrontend(item)),
      finalize(() => this.isLoading.set(false))
    );
  }

  deleteProduct(id: number): Observable<void> {
    this.isLoading.set(true);
    return this.http.delete<void>(`${this.apiUrl}/${id}`).pipe(
      finalize(() => this.isLoading.set(false))
    );
  }

  // --- ADAPTER ---
  private adaptToFrontend(data: any): Product {
    return {
      id: data.id,
      sku: data.sku,
      name: data.name,
      description: data.description,
      category: data.category,
      measurementUnit: data.measurement_unit, // Mapeo snake -> camel
      price: Number(data.price),
      stock: Number(data.stock),
      isActive: data.is_active
    };
  }
}