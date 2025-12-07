import { Component, OnInit, inject } from '@angular/core';
import { CommonModule, CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { InventoryService, Product } from '../../../core/services/inventory';
import { RouterModule, Router } from '@angular/router';

@Component({
  selector: 'app-product-list',
  standalone: true,
  imports: [CommonModule, FormsModule, CurrencyPipe, RouterModule],
  templateUrl: './product-list.html',
  styleUrls: ['./product-list.scss'], 
})
export class ProductListComponent implements OnInit {
  private inventoryService = inject(InventoryService);
  private titleService = inject(Title);
  private router = inject(Router);

  products: Product[] = [];
  filteredProducts: Product[] = [];
  isLoading = false;
  
  // Opciones de Búsqueda/Filtro
  searchTerm: string = '';
  selectedCategory: string = 'all';
  statusFilter: 'all' | 'ACTIVE' | 'LOW_STOCK' | 'DISCONTINUED' = 'all';

  ngOnInit(): void {
    this.titleService.setTitle('ERP - Gestión de Productos');
    this.loadProducts();
  }

  loadProducts(): void {
    this.isLoading = true;
    this.inventoryService.getProducts().subscribe(data => {
      this.products = data;
      this.applyFilters();
      this.isLoading = false;
    });
  }

  // Lógica de Filtrado/Búsqueda
  applyFilters(): void {
    let tempProducts = this.products;

    // 1. Búsqueda por término (name o sku)
    if (this.searchTerm) {
      const searchLower = this.searchTerm.toLowerCase();
      tempProducts = tempProducts.filter(p => 
        p.name.toLowerCase().includes(searchLower) || 
        p.sku.toLowerCase().includes(searchLower)
      );
    }

    // 2. Filtro por Categoría
    if (this.selectedCategory !== 'all') {
      tempProducts = tempProducts.filter(p => p.category === this.selectedCategory);
    }
    
    // 3. Filtro por Status
    if (this.statusFilter !== 'all') {
      tempProducts = tempProducts.filter(p => p.status === this.statusFilter);
    }

    this.filteredProducts = tempProducts;
  }
  
  // Obtiene categorías únicas para el select
  get uniqueCategories(): string[] {
      return [...new Set(this.products.map(p => p.category))];
  }

  // --- Acciones de Administración ---

  editProduct(product: Product): void {
      // Navega a la ruta de edición, asumiendo que el componente product-form maneja la edición
      this.router.navigate(['/inventory/product/edit', product.id]);
  }

  deleteProduct(id: number, name: string): void {
      if (confirm(`¿Está seguro de eliminar el producto "${name}"?`)) {
          this.inventoryService.deleteProduct(id).subscribe({
              next: () => {
                  alert(`Producto "${name}" eliminado exitosamente.`);
                  this.loadProducts(); // Recargar la lista para reflejar el cambio
              },
              error: (err) => {
                  alert('Error al eliminar el producto (MOCK: Error de simulación).');
              }
          });
      }
  }

  navigateToCreate(): void {
      this.router.navigate(['/inventory/product/create']);
  }
}