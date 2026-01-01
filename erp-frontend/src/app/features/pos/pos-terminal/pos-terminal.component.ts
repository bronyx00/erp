import { Component, OnInit, computed, inject, signal, HostListener, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { debounceTime, distinctUntilChanged, switchMap, of, catchError } from 'rxjs';

import { CrmService } from '../../crm/services/crm.service';
import { InventoryService, CategorySummary, Product } from '../../inventory/services/inventory.service';
import { FinanceService, InvoiceCreate, ExchangeRate, PaymentMethod } from '../../../core/services/finance';

import { Customer } from '../../crm/models/customer.model';
import { ClientFormComponent } from '../../crm/client-form/client-form.component';
import { PaymentModalComponent } from '../payment-modal/payment-modal.component';
import { CashCloseModalComponent } from '../../finance/cash-close-modal/cash-close-modal.component';

interface CartItem {
    product: Product;
    quantity: number;
}

@Component({
    selector: 'app-pos-terminal',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, ClientFormComponent, PaymentModalComponent, CashCloseModalComponent],
    templateUrl: './pos-terminal.component.html',
    styleUrls: ['./pos-terminal.component.scss']
})
export class PosTerminalComponent implements OnInit {
    private crmService = inject(CrmService);
    private inventoryService = inject(InventoryService);
    private financeService = inject(FinanceService);

    private round(value: number): number {
        return Math.round((value + Number.EPSILON) * 100) / 100;
    }

    // --- UI Referencias ---
    @ViewChild('searchInput') searchInput!: ElementRef;
    @ViewChild('clientSearchInput') clientSearchInput!: ElementRef;
    @ViewChild('quantityInput') quantityInput!: ElementRef;

    // --- ESTADOS ---
    products = signal<Product[]>([]);
    categories = signal<CategorySummary[]>([]);
    selectedCategory = signal('Todas');
    showCashClose = signal(false);

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
    subtotal = computed(() => {
        const sum = this.cart().reduce((acc, item) => acc + (item.product.price * item.quantity), 0);
        return this.round(sum);
    });
    tax = computed(() => this.round(this.subtotal() * 0.16));
    total = computed(() => this.round(this.subtotal() + this.tax()));
    totalVes = computed(() => this.round(this.total() * (this.exchangeRate() || 0)));

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
        const catFilter = category || this.selectedCategory();
        this.inventoryService.getProducts(1, 20, search, catFilter).subscribe({
            next: (res) => {
                const activeProducts = res.data.filter(p => p.is_active);
                this.products.set(activeProducts);
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
        
        if(this.searchInput) this.searchInput.nativeElement.focus();
    }

    // --- CART & CHECKOUT ---

    addToCartClick(product: Product) {
        if (product.stock <= 0 && product.measurement_unit !== 'SERVICE'){ alert('Producto Agotado'); return};

        this.pendingProduct.set(product);
        this.quantityControl.setValue(1); // Por defecto sugiere 1
        this.isQuantityModalOpen.set(true);

        // 3. Foco automático al input de cantidad
        // Esto permite que el cajero solo presione 'Enter' para aceptar el 1,
        // o escriba '5' + 'Enter' rápidamente.
        setTimeout(() => {
            if(this.quantityInput) {
                this.quantityInput.nativeElement.focus();
                this.quantityInput.nativeElement.select();
            }
        }, 100);
    }

    /** Acción del pequeño modal de cantidad */
    confirmQuantityToAdd() {
        if(this.quantityControl.invalid || !this.pendingProduct()) return;

        let qty = this.quantityControl.value || 1;
        const product = this.pendingProduct()!;

        if (product.measurement_unit === 'UNIT') {
            if (!Number.isInteger(qty)) {
                qty = Math.round(qty);
                if (qty < 1) qty = 1;
            }
        }

        const success = this.processAddToCart(product, qty);

        if (success) {
            // Solo si se agregó (hay stock), cerramos el modal y limpiamos
            this.isQuantityModalOpen.set(false);
            this.pendingProduct.set(null);
            this.quantityControl.setValue(1); // Reset control
            if(this.searchInput) this.searchInput.nativeElement.focus();
        } else {
            // Si falló (ej. stock insuficiente), mantenemos el modal abierto
            // y seleccionamos el input para que corrija rápido
            this.quantityControl.setValue(product.stock); // Opcional: Sugerir el máximo
            setTimeout(() => this.quantityInput.nativeElement.select(), 100);
        }
    }

    /** 
     * Lógica real de modificación del carrito 
     * 
     * Maneja validación de stock, redondeo y eliminación si llega a 0.
     */
    processAddToCart(product: Product, qtyToAdd: number): boolean {
        // 1. Obtener cantidad actual
        const currentItem = this.cart().find(i => i.product.id === product.id);
        const currentQty = currentItem ? currentItem.quantity : 0;
        
        // 2. Calcular final con precisión para evitar "-0.0000001"
        let finalQty = currentQty + qtyToAdd;
        
        // Redondeo de seguridad (3 decimales para KG/M, enteros para UNIT)
        if (product.measurement_unit === 'UNIT') {
            finalQty = Math.round(finalQty);
        } else {
            finalQty = Math.round(finalQty * 1000) / 1000;
        }

        // 3. CASO: ELIMINAR DEL CARRITO
        // Si la cantidad resultante es 0 o negativa, sacamos el producto.
        if (finalQty <= 0) {
            this.removeFromCart(product.id);
            this.searchInput.nativeElement.focus();
            return true; // Operación exitosa (eliminación es válida)
        }

        // 4. CASO: VALIDACIÓN DE STOCK (Solo si estamos SUMANDO)
        // Si qtyToAdd es negativo, siempre dejamos pasar (estamos devolviendo stock)
        if (qtyToAdd > 0 && product.measurement_unit !== 'SERVICE') {
            if (finalQty > product.stock) {
                const availableToAdd = product.stock - currentQty;
                const msg = availableToAdd > 0 
                    ? `⚠️ Stock insuficiente.\nSolo puedes agregar ${availableToAdd} más.`
                    : `⚠️ Has alcanzado el límite de stock disponible (${product.stock}).`;
                
                alert(msg);
                return false; // Bloqueamos la acción
            }
        }

        // 5. ACTUALIZAR CARRITO
        this.cart.update(items => {
            if (currentItem) {
                return items.map(i => i.product.id === product.id ? { ...i, quantity: finalQty } : i);
            }
            return [...items, { product, quantity: finalQty }];
        });

        return true;
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

    handlePaymentConfirm(event: { method: string, amount: number, currency: string, reference?: string }) {
        if (!this.selectedCustomer()) {
            alert('Error: Debe asignar un cliente (F4)'); 
            this.isPaymentModalOpen.set(false);
            return;
        }

        let finalAmount = event.amount;

        if (event.currency === 'VES') {
            finalAmount = event.amount * this.exchangeRate();
        }

        const invoicePayload: InvoiceCreate = {
            customer_tax_id: this.selectedCustomer()!.taxId || 'V-00000000',
            salesperson_id: 1, // TODO: Obtener del AuthService user.id
            currency: event.currency,
            items: this.cart().map(item => ({
                product_id: item.product.id,
                quantity: item.quantity
            })),
            payment: {
                amount: finalAmount,
                payment_method: event.method as PaymentMethod,
                reference: event.reference || `POS-${Date.now().toString().slice(-4)}`,
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

    // --- CIERRE DE CAJA ---
    handleCashClose(success: boolean) {
        this.showCashClose.set(false);
        if (success) {
            // Opcional: Redirigir a login o limpiar pantalla
            alert('Caja cerrada correctamente.');
        }
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
            if (this.isPaymentModalOpen()) return;
            event.preventDefault();
            if(this.searchInput) this.searchInput.nativeElement.focus();
        }
        if (event.key === 'F4') {
            event.preventDefault();
            this.openCustomerDrawer();
        }
    }
}