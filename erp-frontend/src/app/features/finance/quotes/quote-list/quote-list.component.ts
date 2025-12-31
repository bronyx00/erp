import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule, FormControl, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs';

import { FinanceService, Quote } from '../../../../core/services/finance';
import { QuoteDetailModalComponent } from '../quote-detail-modal/quote-detail-modal.component';
import { SkeletonTableComponent } from '../../../../shared/components/skeleton-table/skeleton-table.component';

@Component({
  selector: 'app-quote-list',
  standalone: true,
  imports: [
    CommonModule, RouterLink, CurrencyPipe, DatePipe, 
    QuoteDetailModalComponent, ReactiveFormsModule, 
    FormsModule, SkeletonTableComponent
  ],
  templateUrl: './quote-list.component.html'
})
export class QuoteListComponent implements OnInit {
  private financeService = inject(FinanceService);
  
  // Estados
  quotes = signal<Quote[]>([]);
  isLoading = signal(true);
  selectedQuote = signal<Quote | null>(null);

  // Filtros
  searchControl = new FormControl('');
  currentStatus = signal<string>('');

  // Paginación
  currentPage = signal(1);
  pageSize = signal(10);
  totalItems = signal(0);

  // Computed para paginator
  paginationState = computed(() => {
    const total = this.totalItems();
    const current = this.currentPage();
    const size = this.pageSize();
    const start = total === 0 ? 0 : (current - 1) * size + 1;
    const end = Math.min(current * size, total);
    return { start, end, total, hasNext: current * size < total, hasPrev: current > 1 };
  })

  ngOnInit() {
    this.loadQuotes();

    this.searchControl.valueChanges.pipe(
      debounceTime(400),
      distinctUntilChanged()
    ).subscribe(() => {
      this.currentPage.set(1); // Reset pagina al buscar
      this.loadQuotes();
    });
  }

  loadQuotes() {
    this.isLoading.set(true);
    this.financeService.getQuotes(
        this.currentPage(),
        this.pageSize(),
        this.searchControl.value || '',
        this.currentStatus() || undefined
    ).subscribe({
      next: (res) => {
        this.quotes.set(res.data);
        this.totalItems.set(res.meta.total);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false)
    });
  }
  
  setStatus(status: string) {
    if (this.currentStatus() === status) return;
      this.currentStatus.set(status);
      this.currentPage.set(1);
      this.loadQuotes();
  }

  changePage(page: number) {
    if (page < 1) return;
      this.currentPage.set(page);
      this.loadQuotes();
  }

  openDetail(quote: Quote) {
      this.selectedQuote.set(quote);
  }

  handleConvertFromModal(quote: Quote) {
      this.convertToInvoice(quote);
      this.selectedQuote.set(null); // Cierra el modal tras convertir
  }

  convertToInvoice(quote: Quote) {
    if(!confirm(`¿Convertir cotización ${quote.quote_number} en Factura Real?`)) return;

    this.financeService.convertQuoteToInvoice(quote.id).subscribe({
      next: (invoice) => {
        alert(`✅ Factura #${invoice.invoice_number} generada con éxito.`);
        this.loadQuotes(); // Recargar para ver cambio de estado
      },
      error: (err) => alert('Error al convertir: ' + err.error?.detail)
    });
  }

  isExpired(dateStr: string): boolean {
    return new Date(dateStr) < new Date();
  }

  getStatusClass(status: string) {
    switch(status) {
      case 'SENT': return 'bg-blue-50 text-blue-700 border-blue-100';
      case 'INVOICED': return 'bg-emerald-50 text-emerald-700 border-emerald-100';
      case 'REJECTED': return 'bg-rose-50 text-rose-700 border-rose-100';
      default: return 'bg-slate-50 text-slate-600 border-slate-100';
    }
  }

  getStatusLabel(status: string) {
    const map: any = { 'SENT': 'ENVIADA', 'INVOICED': 'FACTURADA', 'DRAFT': 'BORRADOR' };
    return map[status] || status;
  }
}