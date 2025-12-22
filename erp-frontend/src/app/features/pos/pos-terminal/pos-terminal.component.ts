import { Component, OnInit, computed, inject, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs';

import { PosService } from '../services/pos.service';
import { Product } from '../models/pos.model';
import { CrmService } from '../../crm/services/crm.service'; 
import { Customer } from '../../crm/models/customer.model';

@Component({
  selector: 'app-pos-terminal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './pos-terminal.component.html',
  styleUrls: ['./pos-terminal.component.scss']
})
export class PosTerminalComponent implements OnInit {
  // Inyecciones de Servicios 
  private posService = inject(PosService);
  private crmService = inject(CrmService); // Para buscar clientes

  // --- STATE LOCAL (UI Only) ---
  // Datos que solo importan a esta pantalla (filtros, modales abiertos)
  products = signal<Product[]>([]); 
  categories = signal<string[]>(['Todas', 'Bebidas', 'Alimentos', 'Limpieza', 'Varios']);
  selectedCategory = signal('Todas');
  
  // Conectamos con los Signals del Servicio (Read-only para el template)
  cart = this.posService.cart;
  subtotal = this.posService.subtotal;
  tax = this.posService.tax;
  total = this.posService.total;

  // Cliente seleccionado
  selectedCustomer = signal<Customer | null>(null);
  
  // UI Flags
  isCheckoutOpen = signal(false);
  isCustomerDrawerOpen = signal(false);
  customerList = signal<Customer[]>([]);

  // Search Controls
  searchControl = new FormControl('');
  customerSearchControl = new FormControl('');

  constructor() {
    // Carga inicial de productos Dummy (Aquí llamarías a un InventoryService real)
    this.loadMockProducts();

    // Setup Buscador Clientes (Reactive)
    this.customerSearchControl.valueChanges.pipe(
      debounceTime(300), 
      distinctUntilChanged()
    ).subscribe(term => {
      if (term && term.length > 2) {
        this.crmService.getCustomers(1, 5, term).subscribe(res => this.customerList.set(res.data));
      }
    });
  }

  ngOnInit() {}

  // --- PROXIES AL SERVICIO ---
  // El componente delega la lógica compleja al servicio
  addToCart(p: Product) { this.posService.addToCart(p); }
  removeFromCart(id: number) { this.posService.removeFromCart(id); }
  updateQuantity(id: number, d: number) { this.posService.updateQuantity(id, d); }
  
  clearCart() { 
    this.posService.clearCart(); 
    this.selectedCustomer.set(null);
  }

  processCheckout() {
    this.posService.processSale(this.selectedCustomer()?.id || null);
    this.isCheckoutOpen.set(false);
  }

  // --- FILTROS UI ---
  filterByCategory(cat: string) { this.selectedCategory.set(cat); }

  filteredProducts = computed(() => {
    const cat = this.selectedCategory();
    const term = this.searchControl.value?.toLowerCase() || '';
    return this.products().filter(p => {
      const matchesCat = cat === 'Todas' || p.category === cat;
      const matchesSearch = p.name.toLowerCase().includes(term) || p.sku.toLowerCase().includes(term);
      return matchesCat && matchesSearch;
    });
  });

  // --- CUSTOMER UI ACTIONS ---
  selectCustomer(c: Customer) {
    this.selectedCustomer.set(c);
    this.isCustomerDrawerOpen.set(false);
    this.customerSearchControl.setValue('');
  }

  // --- SHORTCUTS ---
  @HostListener('window:keydown', ['$event'])
  handleKeyboardEvent(event: KeyboardEvent) {
    if (event.key === 'F9') {
      event.preventDefault();
      this.isCheckoutOpen.set(true);
    }
    if (event.key === 'Escape') {
      this.isCheckoutOpen.set(false);
      this.isCustomerDrawerOpen.set(false);
    }
  }

  private loadMockProducts() {
    this.products.set([
      { id: 1, name: 'Café Premium 500g', price: 12.50, stock: 45, category: 'Alimentos', sku: 'CAF-001' },
      { id: 2, name: 'Agua Mineral 1L', price: 1.50, stock: 120, category: 'Bebidas', sku: 'AGU-002' },
      { id: 3, name: 'Jabón Líquido Ind.', price: 5.00, stock: 30, category: 'Limpieza', sku: 'JAB-003' },
      { id: 4, name: 'Galletas Avena', price: 3.20, stock: 50, category: 'Alimentos', sku: 'GAL-004' },
      { id: 5, name: 'Refresco Cola', price: 2.00, stock: 80, category: 'Bebidas', sku: 'REF-005' },
      { id: 6, name: 'Detergente Polvo', price: 8.50, stock: 15, category: 'Limpieza', sku: 'DET-006' },
    ]);
  }
}