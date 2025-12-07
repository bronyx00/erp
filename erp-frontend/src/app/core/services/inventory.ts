import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';

export interface Product {
  id: number;
  sku: string;
  name: string;
  price: number;
  stock: number;
  status?: 'ACTIVE' | 'LOW_STOCK' | 'DISCONTINUED';
  category: string;
  // NOTA: CAMBIAR MODELOS DE PRODUCTO PARA DIFERENCIAR CUANDO UN PRODUCTO SE VENDA POR
  // UNIDAD O POR KILO Y VARIAR EL PRECIO DEPENDIENDO DE ESO.
}

const MOCK_PRODUCTS: Product[] = [
  { id: 101, name: 'Laptop Pro X', sku: 'LTPRX1', price: 1250.00, stock: 15, status: 'ACTIVE', category: 'Electrónica', },
  { id: 102, name: 'Monitor 27" 4K', sku: 'MON4K7', price: 350.00, stock: 5, status: 'LOW_STOCK', category: 'Electrónica', },
  { id: 103, name: 'Mouse Inalámbrico', sku: 'MOUWIR', price: 25.50, stock: 200, status: 'ACTIVE', category: 'Accesorios', },
  { id: 104, name: 'Teclado Mecánico', sku: 'TECKME', price: 89.99, stock: 75, status: 'DISCONTINUED', category: 'Accesorios', },
  { id: 105, name: 'Cable USB-C 2M', sku: 'CABLEC', price: 8.00, stock: 500, status: 'ACTIVE', category: 'Accesorios', },
];

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
   * Busca producto por SKU o nombre.
   */
  searchProducts(query: string): Observable<Product[]> {
    if (!query) return of([]);
    const lowerQuery = query.toLowerCase();

    const results = MOCK_PRODUCTS.filter(p =>
      p.name.toLowerCase().includes(lowerQuery) ||
      p.sku.toLowerCase().includes(lowerQuery)
    );

    return of(results)
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

  /**
   * Método para eliminar un producto del inventario
   */
  deleteProduct(id: number): Observable<void> {
    console.log(`MOCK: Eliminando producto #${id}.`);
    return of(undefined);
  }
}
 