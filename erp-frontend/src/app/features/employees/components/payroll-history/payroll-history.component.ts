import { Component, OnInit, inject, signal, Input, computed } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
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
    // Al buscar, reseteamos a página 1 y recargamos
        this.searchQuery.set(value);
        this.currentPage.set(1); 
        this.loadHistory();
    }

    // Estados
    payrolls = signal<Payroll[]>([]);
    isLoading = signal(true);
    isDeleting= signal(false);

    // Pagination State
    currentPage = signal(1);
    pageSize = signal(20); // N nóminas por página
    totalItems = signal(0);

    // Filter State
    currentFilter = signal<PayrollStatusFilter>('ALL');

    // Selection State
    showPreviewModal = signal(false);
    selectedIds = signal<number[]>([]); // Selección para pago masivo

    // Cálculo de totales de paginación para el UI
    paginationState = computed(() => {
        const total = this.totalItems();
        const current = this.currentPage();
        const size = this.pageSize();

        const start = total === 0 ? 0 : (current - 1) * size + 1;
        const end = Math.min(current * size, total);
        const totalPages = Math.ceil(total / size);

        return { start, end, total, totalPages, hasNext: current < totalPages, hasPrev: current > 1 };
    })

    // Resumen de selección
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

        const query = this.searchQuery().trim();
        const status = this.currentFilter();

        this.hhrrService.getPayrolls(
            this.currentPage(), 
            this.pageSize(), 
            query, 
            status 
        ).subscribe({
            next: (res) => {
                this.payrolls.set(res.data);
                this.totalItems.set(res.meta.total);
                this.isLoading.set(false);
            },
            error: () => {
                this.payrolls.set([]);
                this.isLoading.set(false);
            }
        });
    }

    // --- ACCIONES DE UI ---

    setFilter(filter: PayrollStatusFilter) {
        if (this.currentFilter() === filter) return;

        this.currentFilter.set(filter);
        this.selectedIds.set([]); // Limpiamos selección
        this.currentPage.set(1);    // Reset a página 1
        this.loadHistory();  // Recargar
    }

    changePage(newPage: number) {
        if (newPage < 1 || newPage > this.paginationState().totalPages) return;
        this.currentPage.set(newPage);
        this.selectedIds.set([]); // Opcional: limpiar selección al cambiar de página para evitar confusiones
        this.loadHistory();
    }

    // --- SELECCIÓN & OPERACIONES ---

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
        const ids = this.selectedIds();
        const count = ids.length;

        if (count === 0) return;
        if (!confirm(`¿Estás seguro de eliminar ${count} nóminas pendientes?`)) return;

        this.isDeleting.set(true);

        this.hhrrService.deletePayrollBatch(ids).subscribe({
            next: (response) => {
                // Manejo de respuesta del backend (según tu endpoint python)
                if (response.status === 'warning') {
                    alert(response.message); // Ej: "No se eliminaron porque estaban pagados"
                } else {
                // Éxito
                    this.selectedIds.set([]); // Limpiamos selección
                    this.loadHistory();  // Recargamos tabla
                }
                this.isDeleting.set(false);
            },
            error: (err) => {
                console.error(err);
                alert('Error al eliminar los registros. Intenta nuevamente.');
                this.isDeleting.set(false);
            }
        });
    }
}