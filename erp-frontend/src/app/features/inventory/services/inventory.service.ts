import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { map, Observable, finalize } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Product, ProductPayload, PaginatedProductResult } from '../models/product.model';

export interface PaginatedResponse<T> {
    data: T[];
    meta: {
        total: number;
        page: number;
        limit: number;
        total_pages: number;
    };
}

export interface CategorySummary {
    name: string;
    count: number;
}

@Injectable({ providedIn: 'root' })
export class InventoryService {
    private http = inject(HttpClient);
    private apiUrl = `${environment.apiUrl}/inventory`;

    getProducts(page: number = 1, limit: number = 20, search?: string, category?: string): Observable<PaginatedResponse<Product>> {
        let params = new HttpParams()
        .set('page', page)
        .set('limit', limit);
        
        if (search) params = params.set('search', search);
        if (category && category !== 'Todas') params = params.set('category', category);

        return this.http.get<PaginatedResponse<Product>>(`${this.apiUrl}/products`, { params });
    }

    getCategories(): Observable<CategorySummary[]> {
        return this.http.get<CategorySummary[]>(`${this.apiUrl}/categories`);
    }

    getProductById(id: number): Observable<Product> {
        return this.http.get<Product>(`${this.apiUrl}/products/${id}`);
    }

    createProduct(product: Partial<Product>): Observable<Product> {
        return this.http.post<Product>(`${this.apiUrl}/products`, product);
    }

    updateProduct(id: number, product: Partial<Product>): Observable<Product> {
        return this.http.put<Product>(`${this.apiUrl}/products/${id}`, product);
    }

    deleteProduct(id: number): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/products/${id}`);
    }
}