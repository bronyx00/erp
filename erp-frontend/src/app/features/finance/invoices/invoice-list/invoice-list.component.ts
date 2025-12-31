import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { FormControl, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { debounceTime, forkJoin } from 'rxjs';

import { FinanceService, Invoice, PaymentCreate, PaymentMethod } from '../../../../core/services/finance';
import { SkeletonTableComponent } from '../../../../shared/components/skeleton-table/skeleton-table.component';
import { InvoiceDetailModalComponent } from '../invoice-detail-modal/invoice-detail-modal.component';
import { PaymentModalComponent } from '../../../pos/payment-modal/payment-modal.component';

@Component({
    selector: 'app-invoice-list',
    standalone: true,
    imports: [
        CommonModule, ReactiveFormsModule, FormsModule, 
        CurrencyPipe, DatePipe, SkeletonTableComponent,
        InvoiceDetailModalComponent, PaymentModalComponent
    ],
    templateUrl: './invoice-list.component.html'
})
export class InvoiceListComponent implements OnInit {
    private financeService = inject(FinanceService);
    private getLocalDate(): string {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

    invoices = signal<Invoice[]>([]);
    selectedInvoice = signal<Invoice | null>(null);
    isLoading = signal(true);

    // Estado para el Modal de Pago
    paymentInvoice = signal<Invoice | null>(null);
    amountToPayUsd = signal(0);
    amountToPayVes = signal(0);
    currentExchangeRate = signal(0);
    
    // Filtros
    searchControl = new FormControl('');
    statusFilter = signal<string>(''); 
    dateFilter = signal<string>(this.getLocalDate());

    // Paginación
    currentPage = signal(1);
    pageSize = signal(20);
    totalItems = signal(0);

    paginationState = computed(() => {
        const total = this.totalItems();
        const current = this.currentPage();
        const size = this.pageSize();
        const start = total === 0 ? 0 : (current - 1) * size + 1;
        const end = Math.min(current * size, total);
        return { start, end, total, hasNext: current * size < total, hasPrev: current > 1 };
    });

    ngOnInit() {
        this.loadInvoices();
        this.financeService.getCurrentRate().subscribe(rate => {
            if(rate) this.currentExchangeRate.set(Number(rate.rate));
        });

        this.searchControl.valueChanges.pipe(debounceTime(500)).subscribe(() => {
            this.currentPage.set(1);
            this.loadInvoices();
        });
    }

    loadInvoices() {
        this.isLoading.set(true);
        // Si hay fecha seleccionada la enviamos
        const date = this.dateFilter() || undefined;

        this.financeService.getInvoices(
            this.currentPage(),
            this.pageSize(),
            this.searchControl.value || '',
            this.statusFilter() || undefined,
            date
        ).subscribe({
            next: (res) => {
                this.invoices.set(res.data);
                this.totalItems.set(res.meta.total);
                this.isLoading.set(false);
            },
            error: () => this.isLoading.set(false)
        });
    }

    openDetail(invoice: Invoice) {
        this.isLoading.set(true);
        this.financeService.getInvoiceById(invoice.id).subscribe({
            next: (fullInvoice) => {
                this.selectedInvoice.set(fullInvoice);
                this.isLoading.set(false);
            },
            error: () => {
                this.isLoading.set(false);
                alert('Error al cargar detalle');
            }
        });
    }

    // Método para cambiar filtro de estado (Tabs)
    setStatus(status: string) {
        if (this.statusFilter() === status) return;
        this.statusFilter.set(status);
        this.currentPage.set(1);
        this.loadInvoices();
    }

    changePage(page: number) {
        if(page < 1) return;
        this.currentPage.set(page);
        this.loadInvoices();
    }

    // Abrir Modal de Pago con datos de la deuda
    openPayment(invoice: Invoice) {
        const totalPaid = invoice.payments?.reduce((acc, p) => acc + Number(p.amount), 0) || 0;
        const pending = Number(invoice.total_usd) - totalPaid;
        
        if (pending <= 0.01) {
            alert('Esta factura ya está pagada.');
            return;
        }

        // Configurar datos para el modal del POS
        this.paymentInvoice.set(invoice);
        this.amountToPayUsd.set(pending);
        // Calculamos su equivalente en Bs a tasa actual
        this.amountToPayVes.set(pending * this.currentExchangeRate());
    }

    // Versión BLINDADA para depuración
    handlePosPayment(event: { method?: string, amount?: number, currency?: string, reference?: string }) { 
        console.log('🚀 EVENTO RECIBIDO DEL MODAL:', event);

        if (!this.paymentInvoice()) {
            console.error('❌ Error: No hay factura seleccionada en paymentInvoice');
            return;
        }
        
        const invoiceId = this.paymentInvoice()!.id;
        
        // Validación estricta antes de llamar al servicio
        if (!event?.method || !event?.amount || !event?.currency) {
            console.error('❌ Datos incompletos:', event);
            alert('Error: Datos de pago incompletos');
            return;
        }

        console.log('📡 Enviando al Backend:', {
            invoice_id: invoiceId,
            ...event
        });

        this.isLoading.set(true);

        const invoicePayload: PaymentCreate = {
            invoice_id: invoiceId,
            amount: event.amount,
            currency: event.currency,
            payment_method: event.method as PaymentMethod,
            reference: event.reference || `POS-${Date.now().toString().slice(-4)}`,
            notes: 'Pago Manual desde Facturas'
        }

        this.financeService.registerPayment(invoicePayload).subscribe({
            next: (res) => {
                console.log('✅ Factura pagada:', res);
                alert('Pago registrado correctamente');
                this.paymentInvoice.set(null); 
                this.loadInvoices(); 
                this.isLoading.set(false);
            },
            error: (err) => {
                console.error('❌ ERROR BACKEND:', err);
                // Mostrar el mensaje real del backend (ej: "Monto excede la deuda")
                const msg = err.error?.detail || err.message || 'Error desconocido';
                alert('No se pudo procesar el pago: ' + msg);
                this.isLoading.set(false);
            }
        })
    }

    // Helpers de UI
    getStatusBadge(status: string): string {
        switch(status) {
            case 'PAID': return 'bg-emerald-100 text-emerald-700 border-emerald-200';
            case 'PARTIALLY_PAID': return 'bg-amber-100 text-amber-700 border-amber-200';
            case 'VOID': return 'bg-rose-100 text-rose-700 border-rose-200 line-through opacity-70';
            case 'ISSUED': return 'bg-blue-100 text-blue-700 border-blue-200';
            default: return 'bg-slate-100 text-slate-600';
        }
    }

    getStatusLabel(status: string): string {
        const map: any = { 'PAID': 'Pagada', 'PARTIALLY_PAID': 'Abonada', 'VOID': 'Anulada', 'ISSUED': 'Emitida' };
        return map[status] || status;
    }
}