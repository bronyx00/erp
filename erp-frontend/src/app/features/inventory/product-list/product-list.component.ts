import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs';

import { InventoryService, CategorySummary } from '../services/inventory.service';
import { Product } from '../models/product.model';
import { ProductFormComponent } from '../product-form/product-form.component';
import { SkeletonTableComponent } from '../../../shared/components/skeleton-table/skeleton-table.component';

@Component({
    selector: 'app-product-list',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, ProductFormComponent, SkeletonTableComponent],
    templateUrl: './product-list.component.html'
})
export class ProductListComponent implements OnInit {
    private inventoryService = inject(InventoryService);

    // Estados
    products = signal<Product[]>([]);
    categories = signal<CategorySummary[]>([]);
    isLoading = signal(true);

    // Filtros 
    searchControl = new FormControl('');
    currentCategory = signal('Todas');

    // Paginación
    currentPage = signal(1);
    pageSize = signal(20);
    totalItems = signal(0);

    // Drawer / Modal
    isDrawerOpen = signal(false);
    selectedProduct = signal<Product | null>(null);

    // Computed para Paginación
    paginationState = computed(() => {
        const total = this.totalItems();
        const current = this.currentPage();
        const size = this.pageSize();
        
        const start = total === 0 ? 0 : (current - 1) * size + 1;
        const end = Math.min(current * size, total);
        const totalPages = Math.ceil(total / size);
        
        return { start, end, total, totalPages, hasNext: current < totalPages, hasPrev: current > 1 };
    });

    ngOnInit() {
        this.loadCategories();
        this.loadProducts();

        // Buscador
        this.searchControl.valueChanges
        .pipe(debounceTime(400), distinctUntilChanged())
        .subscribe(() => {
            this.currentPage.set(1);
            this.loadProducts();
        });
    }

    loadCategories() {
        this.inventoryService.getCategories().subscribe(cats => this.categories.set(cats));
    }

    loadProducts() {
        this.isLoading.set(true);
        const search = this.searchControl.value || '';
        
        this.inventoryService.getProducts(
            this.currentPage(), 
            this.pageSize(), 
            search, 
            this.currentCategory()
        ).subscribe({
            next: (res) => {
                this.products.set(res.data);
                this.totalItems.set(res.meta.total);
                this.isLoading.set(false);
            },
            error: () => {
                this.products.set([]);
                this.isLoading.set(false);
            }
        });
    }

    // --- Acciones de UI ---
    setCategory(catName: string) {
        this.currentCategory.set(catName);
        this.currentPage.set(1);
        this.loadProducts();
    }

    changePage(newPage: number) {
        if (newPage < 1) return;
        this.currentPage.set(newPage);
        this.loadProducts();
    }

  // --- ACCIONES DEL DRAWER (MODAL) ---
    openCreate() {
        this.selectedProduct.set(null);
        this.isDrawerOpen.set(true);
    }

    openEdit(product: Product) {
        this.selectedProduct.set(product);
        this.isDrawerOpen.set(true);
    }

    closeDrawer() {
        this.isDrawerOpen.set(false);
        this.selectedProduct.set(null);
    }

    handleSave() {
        this.closeDrawer();
        this.loadProducts();
        this.loadCategories();
    }

    deleteProduct(id: number) {
        if(!confirm('¿Estás seguro de eliminar este producto?')) return;
        this.inventoryService.deleteProduct(id).subscribe(() => {
            this.loadProducts();
            this.loadCategories();
        });
    }
}