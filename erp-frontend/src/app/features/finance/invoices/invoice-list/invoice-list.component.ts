import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { FormControl, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { debounceTime } from 'rxjs';

import { FinanceService, Invoice } from '../../../../core/services/finance';
import { SkeletonTableComponent } from '../../../../shared/components/skeleton-table/skeleton-table.component';
import { InvoiceDetailModalComponent } from '../invoice-detail-modal/invoice-detail-modal.component';

@Component({
    selector: 'app-invoice-list',
    standalone: true,
    imports: [
        CommonModule, ReactiveFormsModule, FormsModule, 
        CurrencyPipe, DatePipe, SkeletonTableComponent,
        InvoiceDetailModalComponent
    ],
    templateUrl: './invoice-list.component.html'
})
export class InvoiceListComponent implements OnInit {
    private financeService = inject(FinanceService);

    invoices = signal<Invoice[]>([]);
    selectedInvoice = signal<Invoice | null>(null);
    isLoading = signal(true);
    
    // Filtros
    searchControl = new FormControl('');
    statusFilter = signal<string>(''); 
    dateFilter = signal<string>(''); // YYYY-MM-DD

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

    changePage(page: number) {
        if(page < 1) return;
        this.currentPage.set(page);
        this.loadInvoices();
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