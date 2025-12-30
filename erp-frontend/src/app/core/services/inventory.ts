import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Product {
  id: number;
  sku: string;
  name: string;
  desciption?: string;
  price: number;
  stock: number;
  status?: 'ACTIVE' | 'LOW_STOCK' | 'DISCONTINUED';
  category: string;
  is_active?: boolean;
  // NOTA: CAMBIAR MODELOS DE PRODUCTO PARA DIFERENCIAR CUANDO UN PRODUCTO SE VENDA POR
  // UNIDAD O POR KILO Y VARIAR EL PRECIO DEPENDIENDO DE ESO.
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
  private readonly API_URL = `${environment.apiUrl}/inventory`;

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
   * Busca producto por SKU o nombre.
   */
  searchProducts(query: string): Observable<Product[]> {
    return new Observable(observer => {
      this.getProducts().subscribe(products => {
        if (!query) {
          observer.next([]);
        } else {
          const lower = query.toLowerCase();
          const filtered = products.filter(p =>
            p.name.toLowerCase().includes(lower) || p.sku.toLowerCase().includes(lower)
          );
          observer.next(filtered);
        }
        observer.complete()
      });
    });
  }

  /**
   * Método para eliminar un producto del inventario
   */
  deleteProduct(id: number): Observable<void> {
    console.log(`MOCK: Eliminando producto #${id}.`);
    return of(undefined);
  }

  /**
   * Método para actualizar stock si lo necesitamos luego
   */
  updateStock(id: number, quantity: number): Observable<any> {
    // Asumiendo que tuvieras un endpoint PATCH, por ahora lo dejamos planteado
    return this.http.patch(`${this.API_URL}/products/${id}`, { stock: quantity });
  }
}
 