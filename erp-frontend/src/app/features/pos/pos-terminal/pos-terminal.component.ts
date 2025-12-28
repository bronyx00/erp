import { Component, OnInit, computed, inject, signal, HostListener, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { debounceTime, distinctUntilChanged, switchMap, of, catchError } from 'rxjs';

import { CrmService } from '../../crm/services/crm.service';
import { InventoryService } from '../../inventory/services/inventory.service';
import { FinanceService, InvoiceCreate, ExchangeRate, PaymentMethod } from '../../../core/services/finance';

import { Customer } from '../../crm/models/customer.model';
import { Product } from '../../inventory/models/product.model';

import { PaymentModalComponent } from '../payment-modal/payment-modal.component';
import { ClientFormComponent } from '../../crm/client-form/client-form.component';

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

    // --- UI Referencias ---
    @ViewChild('searchInput') searchInput!: ElementRef;
    @ViewChild('clientSearchInput') clientSearchInput!: ElementRef;
    @ViewChild('quantityInput') quantityInput!: ElementRef;

    // --- ESTADOS ---
    products = signal<Product[]>([]);
    categories = signal<string[]>([]);
    selectedCategory = signal('Todas');

    cart = signal<CartItem[]>([]);
    selectedCustomer = signal<Customer | null>(null);

    // --- ESTADOS DE FINANCE ---
    exchangeRate = signal<number>(0); // Tasa actual
    exchangeSource = signal<string>('---');

    // UI Flags
    isPaymentModalOpen = signal(false);
    isCustomerDrawerOpen = signal(false);
    isCreateClientMode = signal(false); 
    isQuantityModalOpen = signal(false);

    // Búsquedas y Formularios
    searchControl = new FormControl('');
    customerSearchControl = new FormControl('');
    customerList = signal<Customer[]>([]);
    customerSelectedIndex = signal(0);
    customerSearchTerm = signal('');

    // Control de Cantidad (Pesables)
    pendingProduct = signal<Product | null>(null); // Producto esperando cantidad
    quantityControl = new FormControl(1, [Validators.required, Validators.min(0.001)]); // Control para el input decimal

    // --- COMPUTED ---
    subtotal = computed(() => this.cart().reduce((acc, item) => acc + (item.product.price * item.quantity), 0));
    tax = computed(() => this.subtotal() * 0.16);
    total = computed(() => this.subtotal() + this.tax());
    totalVes = computed(() => this.total() * (this.exchangeRate() || 0));

    ngOnInit() {
        this.loadInitialData();
        this.setupSearch();
    }

    loadInitialData() {
        // 1. Cargar Tasa de Cambio
        this.financeService.getCurrentRate().subscribe({
            next: (data: ExchangeRate) => {
                this.exchangeRate.set(data.rate);
                this.exchangeSource.set(data.source);
            },
            error: () => {
                console.warn('No se pudo cargar la tasa. Usando 0.');
                this.exchangeRate.set(0);
            }
        });

        // 2. Cargar Categorías y Productos
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
            debounceTime(150),
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
            // Auto-abrir drawer si no hay cliente al intentar pagar
            this.openCustomerDrawer();
            return;
        }
        this.isPaymentModalOpen.set(true);
    }

    selectCustomer(c: Customer) {
        this.selectedCustomer.set(c);
        this.isCustomerDrawerOpen.set(false);
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

        const invoicePayload: InvoiceCreate = {
            customer_tax_id: this.selectedCustomer()!.taxId || 'V-00000000',
            salesperson_id: 1, // TODO: Obtener del AuthService user.id
            currency: 'USD',
            items: this.cart().map(item => ({
                product_id: item.product.id,
                quantity: item.quantity
            })),
            payment: {
                amount: event.amount,
                payment_method: event.method,
                reference: `POS-${Date.now().toString().slice(-4)}`,
                notes: 'Venta POS Terminal'
            }
        };

        this.financeService.createInvoice(invoicePayload).subscribe({
            next: (invoice) => {
                console.log('✅ Factura Creada:', invoice);
                alert(`Factura #${invoice.invoice_number} Generada!`);

                // Limpieza
                this.isPaymentModalOpen.set(false);
                this.cart.set([]);
                this.selectedCustomer.set(null);
                this.searchInput.nativeElement.focus();
                this.loadProducts(this.searchControl.value || '', this.selectedCategory());
                this.searchInput.nativeElement.focus();
            },
            error: (err) => {
                console.error('❌ Error facturando:', err);
                alert('Error al crear factura. Revise consola.');
            }
        });
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