import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs';
import { InventoryService } from '../services/inventory.service';
import { Product, InventoryMetadata } from '../models/product.model';
import { ProductFormComponent } from '../product-form/product-form.component';

@Component({
  selector: 'app-product-list',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, ProductFormComponent],
  templateUrl: './product-list.component.html'
})
export class ProductListComponent implements OnInit {
  private inventoryService = inject(InventoryService);

  products = signal<Product[]>([]);
  meta = signal<InventoryMetadata>({ total: 0, page: 1, limit: 10, totalPages: 0 });
  isLoading = this.inventoryService.isLoading;
  
  searchControl = new FormControl('');
  
  // Drawer State
  isDrawerOpen = signal(false);
  selectedProduct = signal<Product | null>(null);

  ngOnInit() {
    this.loadData();
    this.searchControl.valueChanges.pipe(
      debounceTime(300), 
      distinctUntilChanged()
    ).subscribe(() => this.loadData(1));
  }

  loadData(page: number = 1) {
    const term = this.searchControl.value || '';
    this.inventoryService.getProducts(page, 10, term).subscribe({
      next: (res) => {
        this.products.set(res.data);
        this.meta.set(res.meta);
      },
      error: (err) => console.error('Error loading products', err)
    });
  }

  deleteProduct(id: number) {
    if(confirm('¿Estás seguro de desactivar este producto?')) {
      this.inventoryService.deleteProduct(id).subscribe(() => this.loadData(this.meta().page));
    }
  }

  // UI Actions
  openCreate() {
    this.selectedProduct.set(null);
    this.isDrawerOpen.set(true);
  }

  openEdit(product: Product) {
    this.selectedProduct.set(product);
    this.isDrawerOpen.set(true);
  }

  onFormSaved() {
    this.isDrawerOpen.set(false);
    this.loadData(this.meta().page);
  }
}