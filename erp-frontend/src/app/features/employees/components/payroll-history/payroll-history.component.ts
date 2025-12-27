import { Component, OnInit, inject, signal, Input, computed } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs';
import { HhrrService, Payroll } from '../../../../core/services/hhrr';

type PayrollStatusFilter = 'ALL' | 'CALCULATED' | 'PAID';

@Component({
  selector: 'app-payroll-history',
  standalone: true,
  imports: [CommonModule, CurrencyPipe, DatePipe, DecimalPipe],
  templateUrl: './payroll-history.component.html'
})
export class PayrollHistoryComponent implements OnInit {
  private hhrrService = inject(HhrrService);
  private searchQuery = signal('');

  @Input() set searchTerm(value: string) {
    this.searchQuery.set(value);
  }

  // Estados
  payrolls = signal<Payroll[]>([]);
  isLoading = signal(true);
  
  // Estado UI
  searchControl = new FormControl('');
  currentFilter = signal<PayrollStatusFilter>('ALL');
  showPreviewModal = signal(false);
  selectedIds = signal<number[]>([]); // Selección para pago masivo

  // Filtrado real en el cliente para respuesta instantánea
  filteredPayrolls = computed(() => {
    let data = this.payrolls();
    const filter = this.currentFilter();
    const query = this.searchQuery().toLowerCase().trim();

    // Filtro Texto
    if (query) {
      data = data.filter(p => 
        p.employee?.first_name.toLowerCase().includes(query) || 
        p.employee?.last_name.toLowerCase().includes(query) || 
        p.employee?.identification.includes(query)
      );
    }

    // Filtro Estado
    if (filter === 'CALCULATED') {
      data = data.filter(p => p.status === 'CALCULATED' || p.status === 'DRAFT');
    } else if (filter === 'PAID') {
      data = data.filter(p => p.status === 'PAID');
    }

    return data;
  });

  // Resumen computado para el modal
  selectionSummary = computed(() => {
    const ids = this.selectedIds();
    const items = this.payrolls().filter(p => ids.includes(p.id));
    return {
      count: items.length,
      total: items.reduce((sum, p) => sum + p.net_pay, 0),
      items: items
    };
  });


  ngOnInit() {
    this.loadHistory();
  }

  loadHistory() {
    this.isLoading.set(true);
    // Traemos todo (o una página grande) para filtrar en cliente como pidió
    this.hhrrService.getPayrolls(1, 10).subscribe({
      next: (res) => {
        this.payrolls.set(res.data);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false)
    });
  }

  setFilter(filter: PayrollStatusFilter) {
    this.currentFilter.set(filter);
    this.selectedIds.set([]);
  }

  // --- SELECCIÓN ---
  
  toggleSelection(id: number) {
    this.selectedIds.update(ids => 
      ids.includes(id) ? ids.filter(x => x !== id) : [...ids, id]
    );
  }

  selectAll(checked: boolean) {
    if (checked) {
      // Solo seleccionamos los que se pueden pagar (CALCULATED/DRAFT)
      const payables = this.payrolls()
        .filter(p => p.status === 'CALCULATED' || p.status === 'DRAFT')
        .map(p => p.id);
      this.selectedIds.set(payables);
    } else {
      this.selectedIds.set([]);
    }
  }

  // --- ACCIONES ---

  initBatchPayment() {
    if (this.selectedIds().length === 0) return;
    this.showPreviewModal.set(true);
  }

  confirmBatchPayment() {
    this.isLoading.set(true);
    const payload = {
      payroll_ids: this.selectedIds(),
      payment_method: 'TRANSFER',
      notes: 'Pago masivo desde Historial'
    };

    this.hhrrService.payPayrollBatch(payload).subscribe({
      next: () => {
        this.showPreviewModal.set(false);
        this.selectedIds.set([]);
        this.loadHistory(); // Recargar para actualizar estados
        alert('Pagos procesados correctamente.');
      },
      error: (err) => {
        console.error(err);
        alert('Error al procesar pagos.');
        this.isLoading.set(false);
      }
    });
  }

  deleteSelected() {
    const count = this.selectedIds().length;
    if (count === 0) return;
    
    if (!confirm(`¿Estás seguro de eliminar ${count} nóminas pendientes? Esta acción no se puede deshacer.`)) return;

    // Actualización Optimista: Las quitamos de la vista inmediatamente
    const idsToRemove = new Set(this.selectedIds());
    
    this.payrolls.update(current => 
        current.filter(p => !idsToRemove.has(p.id))
    );
    
    // Limpiamos selección
    this.selectedIds.set([]);

    // Aquí llamarías a tu backend (ej. forkJoin de deletes o un endpoint bulk)
    // this.hhrrService.deletePayrolls(ids).subscribe(...)
  }

  // Eliminar registro pendiente
  deletePayroll(id: number) {
    if(!confirm('¿Eliminar este registro de nómina pendiente?')) return;
    
    // Aquí iría la llamada al servicio deletePayroll(id)
    // Simulamos optimísticamente:
    this.payrolls.update(prev => prev.filter(p => p.id !== id));
    this.selectedIds.update(ids => ids.filter(x => x !== id));
  }
}