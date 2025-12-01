import { Component, inject, signal, OnInit, computed, ViewChild, ElementRef, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { InventoryService, Product } from '../../core/services/inventory';
import { CartService } from '../../core/services/cart';
import { FinanceService, InvoiceCreate, PaymentCreate } from '../../core/services/finance';
import { AuthService } from '../../core/services/auth';
import { Router } from '@angular/router';
import { HotkeysService } from '../../core/services/hotkeys';
import { printBlob } from '../../core/utils/print';
import { Subscription } from 'rxjs';
import { CrmService, Customer } from '../../core/services/crm';

@Component({
  selector: 'app-pos',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './pos.html',
  styleUrl: './pos.scss',
})
export class PosComponent implements OnInit, OnDestroy {
  private inventoryService = inject(InventoryService);
  private financeService = inject(FinanceService);
  private authService = inject(AuthService);
  private router = inject(Router);
  public cartService = inject(CartService);
  private fb = inject(FormBuilder);
  private hotkeys = inject(HotkeysService);
  private crmService = inject(CrmService)

  // Referencia al input de búsqueda para enfocarlo con F1
  @ViewChild('searchInput') searchInput!: ElementRef;

  private subs: Subscription[] = [];

  // --- ESTADO ---
  products = signal<Product[]>([]);
  searchTerm = signal<string>('');
  customers = signal<Customer[]>([]);

  // Productos filtrados por el buscador
  filteredProducts = computed(() => {
    const term = this.searchTerm().toLowerCase();
    return this.products().filter(p =>
      p.name.toLowerCase().includes(term) || p.sku.toLowerCase().includes(term)
    );
  });

  // --- ESTADO DEL COBRO ---
  isProcessing = false;
  showPaymentModal = false;
  currentInvoiceId: number | null = null;

  // Formulario de Pago 
  paymentForm = this.fb.group({
    amount: [0, [Validators.required, Validators.min(0.01)]],
    payment_method: ['Cash', [Validators.required]], // Por defecto efectivo en caja
    reference: [''],
    customer_tax_id: ['V00000000', [Validators.required]]
  });

  ngOnInit() {
    this.loadProducts();
    this.loadCustomers();
    this.setupHotkeys();
  }

  ngOnDestroy() {
    // Limpiar suscripciones para no duplicar atajos si sale y entra el cajero
    this.subs.forEach(s => s.unsubscribe());
  }

  setupHotkeys() {
    // F1: Enfocar Buscador
    this.subs.push(this.hotkeys.f1$.subscribe(() => {
      this.searchInput.nativeElement.focus();
      // Seleccionar todo el texto
      this.searchInput.nativeElement.select();
    }));

    // F5: Cobrar
    this.subs.push(this.hotkeys.f5$.subscribe(() => {
      if (!this.showPaymentModal && this.cartService.items().length > 0) {
        this.initiateCheckout();
      } else if (this.showPaymentModal) {
        this.confirmPayment(); // Doble F5 confirmar el pago
      }
    }));

    // ESC: Cancelar / Limpiar
    this.subs.push(this.hotkeys.esc$.subscribe(() => {
      if (this.showPaymentModal) {
        this.cancelCheckout();
      } else {
        this.cartService.clear();
        this.searchTerm.set('');
      }
    }));
  }

  loadProducts() {
    this.inventoryService.getProducts().subscribe({
      next: (data) => this.products.set(data),
      error: (e) => console.error('Error cargando productos:', e)
    });
  }

  loadCustomers() {
    this.crmService.getCustomers().subscribe(data => this.customers.set(data));
  }

  // --- FLUJO DE VENTA ---

  // Botón "Cobrar": Crea la factura y abre el modal
  initiateCheckout() {
    if (this.cartService.items().length === 0) return;

    const taxId = this.paymentForm.value.customer_tax_id;

    if (!taxId) {
      alert('Por favor seleccione un cliente');
      return;
    }

    this.isProcessing = true;

    const invoiceData: InvoiceCreate = {
      customer_tax_id: taxId,
      currency: 'USD',
      items: this.cartService.items().map(item => ({
        product_id: item.product.id,
        quantity: item.quantity
      }))
    };

    this.financeService.createInvoice(invoiceData).subscribe({
      next: (invoice) => {
        this.currentInvoiceId = invoice.id!;

        // Prepara el modal de pago
        this.paymentForm.patchValue({
          amount: invoice.total_usd, // Monto total exacto
          reference: ''
        });

        this.showPaymentModal = true;
        this.isProcessing = false;
      },
      error: (err) => {
        console.error(err);
        alert('Error al crear la orden de venta');
          this.isProcessing = false;
      }
    });
  }

  // Confirmar Pago (Dentro del Modal)
  confirmPayment() {
    if (this.paymentForm.valid && this.currentInvoiceId) {
      this.isProcessing = true;

      const paymentData: PaymentCreate = {
        invoice_id: this.currentInvoiceId,
        amount: this.paymentForm.value.amount!,
        payment_method: this.paymentForm.value.payment_method!,
        reference: this.paymentForm.value.reference || '',
        notes: 'Venta en POS'
      };

      this.financeService.createPayment(paymentData).subscribe({
        next: () => {
          // Éxito
          this.isProcessing = false;
          this.showPaymentModal = false;

          // Impresion automática
          this.printReceipt(this.currentInvoiceId!);

          // Limpiar pantalla
          this.resetPos();
        },
        error: (err) => {
          console.error(err);
          alert('Error registrando el pago');
          this.isProcessing = false;
        }
      });
    }
  }

  // Función dedicada a imprimir
  printReceipt(invoiceId: number) { 
    // Llama al endpoint PDF del backend
    this.financeService.getInvoicePdf(invoiceId).subscribe({
      next: (blob) => {
        printBlob(blob);
      },
      error: () => alert('Error obteniendo el ticket para imprimir')
    });
  }

  cancelCheckout() {
    this.showPaymentModal = false;
    this.currentInvoiceId = null;
  }

  resetPos() {
    this.showPaymentModal = false;
    this.isProcessing = false;
    this.cartService.clear();
    this.currentInvoiceId = null;
    this.paymentForm.reset({
      payment_method: 'Cash',
      customer_tax_id: 'V00000000'
    });
  }

  logout() {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
