import { Component, OnInit, computed, inject, signal, HostListener, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { debounceTime, distinctUntilChanged, switchMap, of, catchError, filter } from 'rxjs';

import { CrmService } from '../../crm/services/crm.service';
import { InventoryService } from '../../inventory/services/inventory.service';
import { FinanceService, InvoiceCreate } from '../../../core/services/finance';

import { Customer } from '../../crm/models/customer.model';
import { Product } from '../../inventory/models/product.model';

import { PaymentModalComponent, PaymentMethod } from '../payment-modal/payment-modal.component';
import { ClientFormComponent } from '../../crm/client-form/client-form.component';

import { InvoiceCreatePayload } from '../models/invoice-payload.model';

interface CartItem {
  product: Product;
  quantity: number;
}

@Component({
  selector: 'app-pos-terminal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, PaymentModalComponent, ClientFormComponent],
  templateUrl: './pos-terminal.component.html',
  styleUrls: ['./pos-terminal.component.scss']
})
export class PosTerminalComponent implements OnInit {
  private crmService = inject(CrmService);
  private inventoryService = inject(InventoryService);
  private financeService = inject(FinanceService);

  // --- STATE ---
  products = signal<Product[]>([]);
  categories = signal<string[]>([]);
  selectedCategory = signal('Todas');
  pendingProduct = signal<Product | null>(null); // Producto esperando cantidad
  isQuantityModalOpen = signal(false);
  quantityControl = new FormControl(1, [Validators.required, Validators.min(0.001)]); // Control para el input decimal
  customerSelectedIndex = signal(0);
  
  cart = signal<CartItem[]>([]);
  selectedCustomer = signal<Customer | null>(null);
  
  // UI Flags
  isPaymentModalOpen = signal(false);
  isCustomerDrawerOpen = signal(false);
  isCreateClientMode = signal(false); 
  
  // Search
  searchControl = new FormControl('');
  customerSearchControl = new FormControl('');
  customerList = signal<Customer[]>([]);
  customerSearchTerm = signal(''); // Para pasar al formulario de creación

  @ViewChild('searchInput') searchInput!: ElementRef;
  @ViewChild('clientSearchInput') clientSearchInput!: ElementRef;
  @ViewChild('quantityInput') quantityInput!: ElementRef; // Referencia para foco automático

  // --- COMPUTED ---
  subtotal = computed(() => this.cart().reduce((acc, item) => acc + (item.product.price * item.quantity), 0));
  tax = computed(() => this.subtotal() * 0.16);
  total = computed(() => this.subtotal() + this.tax());

  ngOnInit() {
    this.loadInitialData();
    this.setupSearch();
  }

  loadInitialData() {
    this.inventoryService.getCategories().subscribe(cats => this.categories.set(cats));
    this.loadProducts();
  }

  loadProducts(search: string = '', category: string = '') {
    // Si la categoría es 'Todas', no mandamos filtro o mandamos string vacío según backend
    this.inventoryService.getProducts(1, 50, search).subscribe({
      next: (res) => {
        let filtered = res.data.filter(p => p.isActive);
        if (category && category !== 'Todas') {
            filtered = filtered.filter(p => p.category === category);
        }
        this.products.set(filtered);
      }
    });
  }

  setupSearch() {
    // Buscador Producto
    this.searchControl.valueChanges.pipe(debounceTime(300), distinctUntilChanged())
      .subscribe(term => this.loadProducts(term || '', this.selectedCategory()));

    // Buscador Cliente
    this.customerSearchControl.valueChanges.pipe(
      debounceTime(150), // Más rápido
      distinctUntilChanged(),
      switchMap(term => {
        this.customerSearchTerm.set(term || '');
        this.customerSelectedIndex.set(0); // Reset selección al buscar
        if (!term) return of({ data: [] });
        return this.crmService.getCustomers(1, 5, term).pipe(catchError(() => of({ data: [] })));
      })
    ).subscribe((res: any) => {
      this.customerList.set(res.data);
    });
  }

  // --- OPEN DRAWER CON FOCUS ---
  openCustomerDrawer() {
    this.isCustomerDrawerOpen.set(true);
    // Hack para esperar que el HTML renderice el input antes de enfocar
    setTimeout(() => {
        if (this.clientSearchInput) {
            this.clientSearchInput.nativeElement.focus();
            this.clientSearchInput.nativeElement.select();
        }
    }, 100);
  }

  // --- NAVEGACIÓN TECLADO CLIENTES ---
  handleClientSearchKeydown(event: KeyboardEvent) {
    const list = this.customerList();
    if (list.length === 0) return;

    if (event.key === 'ArrowDown') {
        event.preventDefault();
        const next = (this.customerSelectedIndex() + 1) % list.length;
        this.customerSelectedIndex.set(next);
    } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        const prev = (this.customerSelectedIndex() - 1 + list.length) % list.length;
        this.customerSelectedIndex.set(prev);
    } else if (event.key === 'Enter') {
        event.preventDefault();
        const selected = list[this.customerSelectedIndex()];
        if (selected) {
            this.selectCustomer(selected);
        }
    }
  }

  // --- KEYWORD & SHORTCUTS ACTIONS ---
  
  onSearchEnter() {
    const term = this.searchControl.value?.trim().toUpperCase();
    if (!term) return;

    // 1. Keyword exacta (SKU)
    const exactMatch = this.products().find(p => p.sku === term);
    if (exactMatch) {
      this.addToCartClick(exactMatch);
      this.searchControl.setValue(''); // Limpiar para siguiente escaneo
      return;
    }

    // 2. Si hay solo un resultado en la lista actual
    if (this.products().length === 1) {
      this.addToCartClick(this.products()[0]);
      this.searchControl.setValue('');
      return;
    }

    // 3. Keyword especial (Ej: "SERV" agrega un item generico)
    if (term === 'GENERICO') {
       // Lógica custom...
    }
  }

  filterByCategory(cat: string) {
    this.selectedCategory.set(cat);
    this.loadProducts(this.searchControl.value || '', cat);
    // Focus back to search for UX
    this.searchInput.nativeElement.focus();
  }

  // --- CART & CHECKOUT ---

  addToCartClick(product: Product) {
    if (product.stock <= 0 && product.measurementUnit !== 'SERVICE') {
        // Sonido de error o feedback visual
        return; 
    }

    if (product.measurementUnit === 'UNIT') {
      // Si es unitario, flujo directo
      this.processAddToCart(product, 1);
    } else {
      // Si es pesable/medible, abrimos modal
      this.pendingProduct.set(product);
      this.quantityControl.setValue(1); // Reset a 1 como sugerencia
      this.isQuantityModalOpen.set(true);
        
      // Foco automático al input de cantidad
      setTimeout(() => {
        if(this.quantityInput) {
          this.quantityInput.nativeElement.focus();
          this.quantityInput.nativeElement.select();
        }
      }, 100);
    }
  }

  /** Acción del pequeño modal de cantidad */
  confirmQuantityToAdd() {
      if(this.quantityControl.invalid || !this.pendingProduct()) return;

      const qty = this.quantityControl.value || 1;
      this.processAddToCart(this.pendingProduct()!, qty);
      
      // Reset states
      this.isQuantityModalOpen.set(false);
      this.pendingProduct.set(null);
      // Devolver foco al buscador principal
      this.searchInput.nativeElement.focus();
  }

  /** Lógica real de modificación del carrito */
  processAddToCart(product: Product, qtyToAdd: number) {
    this.cart.update(items => {
      const existing = items.find(i => i.product.id === product.id);
      if (existing) {
        // Si existe, sumamos la nueva cantidad (puede ser decimal)
        return items.map(i => i.product.id === product.id ? { ...i, quantity: i.quantity + qtyToAdd } : i);
      }
      // Si no, lo agregamos
      return [...items, { product, quantity: qtyToAdd }];
    });
  }

  openPaymentModal() {
    if (this.cart().length === 0) return;
    if (!this.selectedCustomer()) {
      alert('Seleccione un cliente primero'); // O abrir drawer de cliente auto
      this.isCustomerDrawerOpen.set(true);
      return;
    }
    this.isPaymentModalOpen.set(true);
  }

  removeFromCart(productId: number) {
    this.cart.update(items => items.filter(i => i.product.id !== productId))
  }

  handlePaymentConfirm(event: { method: PaymentMethod, amount: number }) {
    if (!this.selectedCustomer()) {
      alert('Error: Debe asignar un cliente (F4)'); 
      this.isPaymentModalOpen.set(false);
      return;
    }

    // Payload exacto para tu Backend
    const payload: InvoiceCreatePayload = {
        customer_tax_id: this.selectedCustomer()!.taxId,
        salesperson_id: 0, // Por ahora 0 o tomar del AuthService
        currency: "USD",
        items: this.cart().map(item => ({
            product_id: item.product.id,
            quantity: item.quantity
        })),
        payment: {
            amount: event.amount,
            payment_method: event.method,
            reference: "POS-" + Date.now().toString().slice(-6), // Generamos ref temporal
            notes: "Venta rápida POS"
        }
    };

    console.log('✅ JSON LISTO PARA BACKEND:', JSON.stringify(payload, null, 2));
    
    // Simulación de éxito
    this.isPaymentModalOpen.set(false);
    this.cart.set([]);
    this.selectedCustomer.set(null);
    this.customerSearchControl.setValue('');
    // Focus back al inicio para siguiente venta
    this.searchInput.nativeElement.focus();
  }

  // --- CLIENT MANAGEMENT ---

  initCreateClient() {
    this.isCreateClientMode.set(true);
  }

  onClientCreated(newClient: Customer) {
    this.selectedCustomer.set(newClient);
    this.isCreateClientMode.set(false);
    this.isCustomerDrawerOpen.set(false);
    this.customerSearchControl.setValue('');
  }

  selectCustomer(c: Customer) {
    this.selectedCustomer.set(c);
    this.isCustomerDrawerOpen.set(false);
  }

  // --- GLOBAL HOTKEYS ---
  @HostListener('window:keydown', ['$event'])
  handleKeys(event: KeyboardEvent) {
    if (event.key === 'Escape') {
        if (this.isQuantityModalOpen()) {
            this.isQuantityModalOpen.set(false);
            this.pendingProduct.set(null);
            this.searchInput.nativeElement.focus();
            return;
        }
        if (this.isPaymentModalOpen()) {
            this.isPaymentModalOpen.set(false);
            return;
        }
        if (this.isCustomerDrawerOpen()) {
            this.isCustomerDrawerOpen.set(false);
            this.searchInput.nativeElement.focus();
            return;
        }
        // Si no hay modales, quitamos foco del buscador principal
        this.searchInput.nativeElement.blur();
        return;
    }
    if (event.key === 'F9') {
        event.preventDefault();
        this.openPaymentModal();
    }
    if (event.key === 'F2') {
        event.preventDefault();
        this.searchInput.nativeElement.focus();
    }
    if (event.key === 'F4') {
        event.preventDefault();
        this.openCustomerDrawer();
    }
  }
}