import { Component, EventEmitter, Output, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { HhrrService, Employee, Payroll } from '../../../../core/services/hhrr';

type Step = 'CONFIG' | 'PREVIEW' | 'SUCCESS';

@Component({
    selector: 'app-payroll-generator',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, CurrencyPipe, DatePipe, DecimalPipe],
    templateUrl: './payroll-generator.component.html'
})
export class PayrollGeneratorComponent implements OnInit {
    private hhrrService = inject(HhrrService);
    private fb = inject(FormBuilder);

    @Output() onClose = new EventEmitter<void>();
    @Output() onFinish = new EventEmitter<void>();

    step = signal<Step>('CONFIG');
    isLoading = signal(false);

    // Data
    employees = signal<Employee[]>([]);
    selectedEmpIds = signal<number[]>([]);

    // Resultados del borrador
    previewPayrolls = signal<Payroll[]>([]);

    configForm!: FormGroup;

    // Computed Totals
    totals = computed(() => {
    const items = this.previewPayrolls();
    return {
        count: items.length,
        earnings: items.reduce((sum, p) => sum + p.total_earnings, 0),
        deductions: items.reduce((sum, p) => sum + p.total_deductions, 0),
        net: items.reduce((sum, p) => sum + p.net_pay, 0)
    };
    });

    ngOnInit() {
        this.initForm();
        this.loadEmployees();
    }

    initForm() {
        const today = new Date();
        // Default: Del 1 al 30 del mes actual
        const start = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
        const end = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split('T')[0];

        this.configForm = this.fb.group({
            start_date: [start, Validators.required],
            end_date: [end, Validators.required],
            select_all: [true]
        });
    }

    loadEmployees() {
        this.hhrrService.getEmployees(1, 1000).subscribe(res => {
            // Solo empleados activos
            const active = res.data.filter(e => e.is_active);
            this.employees.set(active);
            // Seleccionar todos por defecto
            this.selectedEmpIds.set(active.map(e => e.id));
        });
    }

    toggleSelection(id: number) {
        this.selectedEmpIds.update(ids => 
            ids.includes(id) ? ids.filter(x => x !== id) : [...ids, id]
        );
            this.configForm.get('select_all')?.setValue(false, { emitEvent: false });
        }

    toggleSelectAll(checked: boolean) {
        if (checked) {
            this.selectedEmpIds.set(this.employees().map(e => e.id));
        } else {
            this.selectedEmpIds.set([]);
        }
    }

    // --- ACCIÓN 1: GENERAR BORRADOR ---
    generateDraft() {
        if (this.selectedEmpIds().length === 0) return;

        this.isLoading.set(true);
        const val = this.configForm.value;

        const payload = {
            period_start: val.start_date,
            period_end: val.end_date,
            employee_ids: this.selectedEmpIds()
        };

        this.hhrrService.generatePayroll(payload).subscribe({
            next: (res: any) => {
                console.log('✅ Borradores generados', res);
                // Una vez generados, buscamos esos datos para mostrarlos
                this.fetchPreviewData(val.start_date, val.end_date);
            },
            error: (err) => {
                console.error(err);
                alert('Error generando nómina.');
                this.isLoading.set(false);
            }
        });
    }

    fetchPreviewData(start: string, end: string) {
        this.hhrrService.getPayrolls(1, 100, '', 'CALCULATED').subscribe({
            next: (res) => {
                const draftPayrolls = res.data.filter(p => 
                    p.period_start === start && p.period_end === end
                );

                this.previewPayrolls.set(draftPayrolls);
                this.step.set('PREVIEW'); // Avanzamos al paso 2
                this.isLoading.set(false); // Quitamos el loading
            },
            error: (err) => {
                console.error('Error fetching preview', err);
                this.isLoading.set(false);
                alert('Se generó el borrador pero hubo error al cargar la vista previa.');
            }
        });
    }

    // --- ACCIÓN 2: CONFIRMAR PAGO ---
    confirmPayment() {
        this.isLoading.set(true);
        const ids = this.previewPayrolls().map(p => p.id);

        this.hhrrService.payPayrollBatch({
            payroll_ids: ids,
            payment_method: 'TRANSFER',
            notes: 'Pago generado desde Wizard'
        }).subscribe({
        next: () => {
            this.step.set('SUCCESS');
            this.isLoading.set(false);
        },
        error: (err) => {
            console.error(err);
            alert('Error procesando el pago final.');
            this.isLoading.set(false);
        }
        });
    }

    finish() {
        this.onFinish.emit();
        this.onClose.emit();
    }
}