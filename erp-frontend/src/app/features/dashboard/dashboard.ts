import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators, FormArray, FormGroup } from '@angular/forms';
import { FinanceService, Invoice, ExchangeRate, InvoiceCreate, PaymentCreate, DashboardMetrics } from '../../core/services/finance';
import { InventoryService, Product } from '../../core/services/inventory'; 
import { CrmService, Customer } from '../../core/services/crm';
import { AuthService } from '../../core/services/auth';
import { RouterLink } from '@angular/router';
import { printBlob } from '../../core/utils/print';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.scss']
})

export class DashboardComponent implements OnInit {
  private financeService = inject(FinanceService);
  private inventoryService = inject(InventoryService);
  private crmService = inject(CrmService);
  public authService = inject(AuthService);
  private fb = inject(FormBuilder);

  // Signals de Datos
  invoices = signal<Invoice[]>([]);
  products = signal<Product[]>([]);
  customers = signal<Customer[]>([]);
  currentRate = signal<ExchangeRate | null>(null);
  metrics = signal<DashboardMetrics | null>(null);

  userEmail = computed(() => this.authService.currentUser());
  
  // Formularios
  invoiceForm: FormGroup;
  customerForm: FormGroup;
  
  // Variables de UI
  isSubmitting = false;
  showCustomerModal = false;
  successMessage = '';
  errorMessage = '';

  // Variables para Modales de Acción
  showPaymentModal = false;
  selectedInvoice: Invoice | null = null;

  paymentForm = this.fb.group({
    amount: [0, [Validators.required, Validators.min(0.01)]],
    payment_method: ['Tarjeta Débito', [Validators.required]],
    reference: [''],
    notes: ['']
  });

  // Variables Supervisor
  showSupervisorModal = false;
  invoiceToVoidId: number | null = null;
  supervisorForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]]
  });

  constructor() {
    // Inicializar Formulario de Factura
    this.invoiceForm = this.fb.group({
      selectedCustomerTaxId: ['', Validators.required], // <--- CAMBIO: Guardamos el TAX ID
      items: this.fb.array([])
    });

    // Formulario Cliente
    this.customerForm = this.fb.group({
      name: ['', Validators.required],
      email: ['', [Validators.email]],
      tax_id: ['', Validators.required],
      phone: [''],
      address: ['']
    });
  }

  get itemsFormArray() {
    return this.invoiceForm.get('items') as FormArray;
  }

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    // 1. Cargar Facturas
    this.financeService.getInvoices().subscribe({
      next: (data) => this.invoices.set(data),
      error: (err) => console.error('Error facturas', err)
    });

    // 2. Cargar Productos
    this.inventoryService.getProducts().subscribe(data => this.products.set(data));

    // 3. Cargar Clientes
    this.crmService.getCustomers().subscribe(data => this.customers.set(data));

    // 4. Tasa y Métricas
    this.financeService.getCurrentRate().subscribe(r => this.currentRate.set(r));
    this.financeService.getMetrics().subscribe(m => this.metrics.set(m));
  }

  // --- GESTIÓN DE ÍTEMS EN FACTURA ---
  addItem() {
    const itemGroup = this.fb.group({
      product_id: [null, Validators.required],
      quantity: [1, [Validators.required, Validators.min(1)]]
    });
    this.itemsFormArray.push(itemGroup);
  }

  removeItem(index: number) {
    this.itemsFormArray.removeAt(index);
  }

  // --- CREAR FACTURA ---
  onSubmitInvoice() {
    if (this.invoiceForm.valid) {
      this.isSubmitting = true;
      const val = this.invoiceForm.value;

      const invoiceData: InvoiceCreate = {
        customer_tax_id: val.selectedCustomerTaxId, // <--- Enviamos el RIF
        currency: 'USD',
        items: val.items.map((i: any) => ({
          product_id: Number(i.product_id),
          quantity: i.quantity
        }))
      };

      this.financeService.createInvoice(invoiceData).subscribe({
        next: (inv) => {
          this.invoices.update(list => [inv, ...list]);
          this.successMessage = `Factura #${inv.invoice_number} creada con éxito`; // <--- Usamos número real
          this.itemsFormArray.clear();
          this.invoiceForm.patchValue({ selectedCustomerTaxId: '' });
          this.isSubmitting = false;
          this.loadData(); // Recargar métricas
          
          setTimeout(() => this.successMessage = '', 3000);
        },
        error: (err) => {
          console.error(err);
          this.errorMessage = 'Error al crear factura';
          this.isSubmitting = false;
        }
      });
    }
  }

  // --- PAGOS ---
  openPaymentModal(invoice: Invoice) {
    this.selectedInvoice = invoice;
    this.showPaymentModal = true;
    
    // Calcular restante (simple: total - 0 si no tenemos historial de pagos en front)
    // Usamos total_usd que es el nuevo campo
    this.paymentForm.patchValue({
      amount: invoice.total_usd, 
      payment_method: 'Zelle',
      reference: '',
      notes: ''
    });
  }

  closePaymentModal() {
    this.showPaymentModal = false;
    this.selectedInvoice = null;
  }

  onSubmitPayment() {
    if (this.paymentForm.valid && this.selectedInvoice?.id) {
      this.isSubmitting = true;
      const val = this.paymentForm.value;

      const paymentPayload: PaymentCreate = {
        invoice_id: this.selectedInvoice.id,
        amount: val.amount!,
        payment_method: val.payment_method!,
        reference: val.reference || '',
        notes: val.notes || ''
      };

      this.financeService.createPayment(paymentPayload).subscribe({
        next: () => {
          alert('Pago registrado');
          this.closePaymentModal();
          this.isSubmitting = false;
          this.loadData(); // Recargar para ver estado PAID
        },
        error: (err) => {
          this.isSubmitting = false;
          alert('Error registrando pago');
        }
      });
    }
  }

  // --- ANULACIÓN (VOID) ---
  askCancelInvoice(invoice: Invoice) {
    if (invoice.status === 'VOID') return;

    if (invoice.status === 'PAID' || invoice.status === 'PARTIALLY_PAID') {
      this.invoiceToVoidId = invoice.id;
      this.showSupervisorModal = true;
      this.supervisorForm.reset();
    } else {
      if (confirm(`¿Anular Factura #${invoice.invoice_number}?`)) {
        this.executeVoid(invoice.id);
      }
    }
  }

  onSupervisorSubmit() {
    if (this.supervisorForm.valid && this.invoiceToVoidId) {
      const { email, password } = this.supervisorForm.value;
      this.authService.login(email!, password!).subscribe({
        next: (tokenData) => {
          this.executeVoid(this.invoiceToVoidId!, tokenData.access_token);
          this.showSupervisorModal = false;
        },
        error: () => alert('Credenciales inválidas')
      });
    }
  }

  executeVoid(id: number, token?: string) {
    this.financeService.voidInvoice(id, token).subscribe({
      next: (updatedInv) => {
        this.invoices.update(list => list.map(i => i.id === id ? updatedInv : i));
        alert('Factura anulada');
        this.loadData(); // Recargar métricas/stock
      },
      error: (e) => alert('Error anulando: ' + (e.error?.detail || 'Desconocido'))
    });
  }

  // --- PDF ---
  downloadPdf(invoice: Invoice) {
    this.financeService.getInvoicePdf(invoice.id).subscribe(blob => {
      printBlob(blob);
    });
  }

  // --- CLIENTES ---
  openNewCustomerModal() { this.showCustomerModal = true; }
  closeModal() { this.showCustomerModal = false; }

  saveCustomer() {
    if (this.customerForm.valid) {
      this.isSubmitting = true;
      this.crmService.createCustomer(this.customerForm.value).subscribe({
        next: (cust) => {
          this.customers.update(prev => [...prev, cust]);
          this.isSubmitting = false;
          this.closeModal();
          this.customerForm.reset();
          // Seleccionar automáticamente al nuevo
          this.invoiceForm.patchValue({ selectedCustomerTaxId: cust.tax_id });
        },
        error: () => {
          alert('Error creando cliente');
          this.isSubmitting = false;
        }
      });
    }
  }
  
  logout() {
    this.authService.logout();
  }
}