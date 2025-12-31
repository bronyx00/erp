import { Component, inject, signal, computed, OnInit, ViewChild, ElementRef } from '@angular/core';
import { CommonModule, DatePipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Subject, debounceTime, distinctUntilChanged, switchMap, of } from 'rxjs';

import { FinanceService, QuoteCreate } from '../../../../core/services/finance';
import { InventoryService, Product } from '../../../inventory/services/inventory.service';
import { CrmService } from '../../../../features/crm/services/crm.service'; 
import { AuthService } from '../../../../core/services/auth';
import { CustomerPayload } from '../../../crm/models/customer.model';

interface FormItem {
  productId?: number;
  productName: string;
  quantity: number;
  unitPrice: number; // Precio en la moneda seleccionada
  basePriceUsd: number; // Precio base para conversiones
}

@Component({
  selector: 'app-quote-form',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, DatePipe, DecimalPipe],
  templateUrl: './quote-form.component.html' // Cambiaremos esto según el diseño que elijas
})
export class QuoteFormComponent implements OnInit {
  private financeService = inject(FinanceService);
  private inventoryService = inject(InventoryService);
  private crmService = inject(CrmService); // Asumiendo que tienes este servicio
  private authService = inject(AuthService);
  private router = inject(Router);
  private searchSubject = new Subject<string>();

  @ViewChild('searchInput') searchInput!: ElementRef;

  // --- DATOS GLOBALES ---
  companyData = signal<any>(null);
  exchangeRate = signal<number>(0);
  today = new Date();
  
  // --- FORMULARIO ---
  dateExpires = new Date(new Date().setDate(new Date().getDate() + 15)).toISOString().split('T')[0];
  currency = signal<'USD' | 'VES'>('USD');
  currencySymbol = computed(() => this.currency() === 'USD' ? '$' : 'Bs.')
  
  // Cliente
  customerRif = '';
  customerName = '';
  customerPhone = '';
  customerAddress = '';
  customerEmail = '';
  isSearchingClient = false;
  clientFound = false; // Controla si se bloquean los campos o no
  isCreatingClient = false;

  // Items
  items = signal<FormItem[]>([
    { productName: '', quantity: 1, unitPrice: 0, basePriceUsd: 0 }
  ]);

  // Totales
  subtotal = computed(() => this.items().reduce((acc, i) => acc + (i.quantity * i.unitPrice), 0));
  tax = computed(() => this.subtotal() * 0.16);
  total = computed(() => this.subtotal() + this.tax());

  // Extras
  notes = '';
  terms = 'Validez de la oferta: 15 días. Precios sujetos a cambio sin previo aviso.';
  isSaving = false;

  // Modales
  isProductModalOpen = false;
  productSearchTerm = '';
  productResults = signal<Product[]>([]);
  activeItemIndex: number | null = null; // Para saber qué fila está buscando

  ngOnInit() {
    // 1. Cargar Datos de la Empresa (Usuario actual -> Tenant)
    this.authService.me().subscribe(user => {
       // Aquí podrías tener un endpoint específico para datos públicos del tenant
       // O usar los datos que vienen en el token/user si están disponibles.
       // Por ahora simulamos con datos del usuario si el backend no trae "tenant_info" directo en /me
       this.companyData.set({
         name: 'Cargando empresa...', // Idealmente esto viene de un servicio
         rif: 'J-...'
       });
       
       // Si tienes un endpoint getTenantSettings o similar, úsalo aquí.
    });

    // 2. Cargar Tasa de Cambio
    this.financeService.getCurrentRate().subscribe(rate => {
      if(rate) this.exchangeRate.set(Number(rate.rate));
    });

    this.searchSubject.pipe(
      debounceTime(200), // Espera 300ms tras dejar de escribir
      distinctUntilChanged() // Evita buscar lo mismo dos veces
    ).subscribe(term => {
      this.performSearch(term);
    });
  }

  // --- LÓGICA DE MONEDA ---
  toggleCurrency() {
    const newCurrency = this.currency() === 'USD' ? 'VES' : 'USD';
    this.currency.set(newCurrency);
    this.recalculatePrices();
  }

  recalculatePrices() {
    const rate = this.exchangeRate();
    if (rate <= 0) return;

    this.items.update(currentItems => {
      return currentItems.map(item => {
        let newPrice = 0;
        if (this.currency() === 'VES') {
          // Convertir de Base USD a VES
          newPrice = item.basePriceUsd * rate;
        } else {
          // Volver a USD
          newPrice = item.basePriceUsd;
        }
        return { ...item, unitPrice: newPrice };
      });
    });
  }

  // --- LÓGICA DE CLIENTE ---
  searchCustomer() {
    if (!this.customerRif) return;
    this.isSearchingClient = true;
    
    // Asumiendo un método en CrmService
    this.crmService.getCustomers(1, 1, this.customerRif).subscribe({
      next: (res) => {
        if (res.data && res.data.length > 0) {
          const client = res.data[0];
          this.customerName = client.name;
          this.customerPhone = client.phone!;
          this.customerAddress = client.address!;
          this.customerEmail = client.email || '';
          this.clientFound = true;
        } else {
          // No encontrado
          this.clientFound = false;
          this.customerName = ''; // Limpiar para que escribe
          this.customerPhone = '';
          this.customerAddress = '';
          this.customerEmail = '';
        }
        this.isSearchingClient = false;
      },
      error: () => {
        this.isSearchingClient = false;
        this.clientFound = false;
      }
    });
  }

  // --- LÓGICA DE PRODUCTOS ---
  openProductSearch(index: number) {
    this.activeItemIndex = index;
    this.isProductModalOpen = true;
    this.productSearchTerm = '';
    this.productResults.set([]);
    
    // Auto-Focus al abrir el modal
    setTimeout(() => {
        if(this.searchInput) this.searchInput.nativeElement.focus();
    }, 100);
  }

  // Método llamado por el Input HTML
  onSearchInput(term: string) {
    this.searchSubject.next(term);
  }

  // Búsqueda real contra la API
  performSearch(term: string) {
    if (!term) {
        this.productResults.set([]);
        return;
    }
    this.inventoryService.getProducts(1, 20, term).subscribe(res => {
      this.productResults.set(res.data);
    });
  }

  selectProduct(product: Product) {
    if (this.activeItemIndex === null) return;

    const rate = this.exchangeRate();
    let finalPrice = Number(product.price); // Precio Base (USD)

    // Si estamos en VES, convertimos al momento de seleccionar
    if (this.currency() === 'VES' && rate > 0) {
      finalPrice = finalPrice * rate;
    }

    this.items.update(items => {
      const newItems = [...items];
      newItems[this.activeItemIndex!] = {
        productId: product.id,
        productName: product.name, // + (product.sku ? ` (${product.sku})` : ''), // Opcional agregar SKU al nombre
        quantity: 1,
        basePriceUsd: Number(product.price),
        unitPrice: finalPrice
      };
      return newItems;
    });

    this.isProductModalOpen = false;
    this.activeItemIndex = null;
  }

  updateItem(index: number, field: 'quantity' | 'unitPrice' | 'productName', value: any) {
    this.items.update(currentItems => {
      // Creamos una copia del array para mantener inmutabilidad
      const newItems = [...currentItems];
      // Actualizamos el campo específico
      newItems[index] = { ...newItems[index], [field]: value };
      return newItems;
    });
  }

  // --- CRUD ITEMS ---
  addItem() {
    this.items.update(i => [...i, { productName: '', quantity: 1, unitPrice: 0, basePriceUsd: 0 }]);
  }

  removeItem(index: number) {
    this.items.update(i => i.filter((_, idx) => idx !== index));
  }

  // --- GUARDAR ---
  saveQuote() {
    if (this.items().length === 0 || !this.customerName) return;
    this.isSaving = true;

    const payload: QuoteCreate = {
      customer_tax_id: this.customerRif,
      date_expires: this.dateExpires,
      currency: this.currency(),
      items: this.items().map(i => ({
        product_id: i.productId || 0, // 0 si es item manual
        quantity: i.quantity,
        unit_price: i.unitPrice, // Enviamos el precio ya convertido o en USD según la selección
        description: i.productName
      })),
      notes: this.notes,
      terms: this.terms
    };

    let process$;

    if (!this.clientFound) {
      // CLIENTE NUEVO -> Crea Cliente
      const newClient: CustomerPayload = {
        tax_id: this.customerRif,
        name: this.customerName,
        phone: this.customerPhone,
        address: this.customerAddress,
        email: this.customerEmail
      };

      process$ = this.crmService.createCustomer(newClient).pipe(
        // Una vez creado el cliente, crea la cotización
        switchMap(() => this.financeService.createQuote(payload))
      )
    } else {
      // CLIENTE EXISTE -> Solo crea Cotización
      process$ = this.financeService.createQuote(payload)
    }

    process$.subscribe({
      next: (res) => {
        alert('✅ Cotización guardada con éxito.');
        if (!this.clientFound) alert('👤 Cliente nuevo registrado automáticamente.');
        
        this.router.navigate(['/quotes']);
      },
      error: (err) => {
        console.error(err);
        this.isSaving = false;
        alert('Error al procesar: ' + (err.error?.detail || 'Verifique los datos'));
      }
    });
  }
}