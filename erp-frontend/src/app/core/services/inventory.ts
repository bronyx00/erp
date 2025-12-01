import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Product {
  id: number;
  sku: string;
  name: string;
  price: number;
  stock: number;
}

export interface ProductCreate {
  sku: string;
  name: string;
  description?: string;
  price: number;
  stock: number;
}

@Injectable({
  providedIn: 'root',
})
export class InventoryService {
  private http = inject(HttpClient);
  private readonly API_URL = 'http://localhost:80/api/inventory';

  /**
   * Obtiene todos los productos de la empresa actual.
   */
  getProducts(): Observable<Product[]> {
    return this.http.get<Product[]>(`${this.API_URL}/products`);
  }

  /**
   * Obtiene un producto específico por ID.
   */
  getProductById(id: number): Observable<Product> {
    return this.http.get<Product>(`${this.API_URL}/products/${id}`);
  }

  /**
   * Crea un nuevo producto en el inventario.
   * @param product Datos del producto a crear
   */
  createProduct(product: ProductCreate): Observable<Product> {
    return this.http.post<Product>(`${this.API_URL}/products`, product);
  }

  /**
   * Método para actualizar stock si lo necesitamos luego
   */
  updateStock(id: number, quantity: number): Observable<any> {
    // Asumiendo que tuvieras un endpoint PATCH, por ahora lo dejamos planteado
    return this.http.patch(`${this.API_URL}/products/${id}`, { stock: quantity });
  }
}
 