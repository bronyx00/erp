import { Component, EventEmitter, Output, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators, FormArray } from '@angular/forms';
import { HhrrService, WorkSchedule } from '../../../../core/services/hhrr';

@Component({
    selector: 'app-schedule-manager',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule],
    templateUrl: './schedule-manager.component.html',
    host: { class: 'block h-full' }
})
export class ScheduleManagerComponent implements OnInit {
    private fb = inject(FormBuilder);
    private hhrrService = inject(HhrrService);

    @Output() onClose = new EventEmitter<void>();
    @Output() onSelect = new EventEmitter<WorkSchedule>(); // Opcional si quisieras seleccionar al crear

    schedules = signal<WorkSchedule[]>([]);
    viewMode = signal<'LIST' | 'CREATE'>('LIST');
    isLoading = signal(false);
    isSubmitting = signal(false);

    // Formulario Dinámico
    form!: FormGroup;
    weekDays = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

    // Mapping para el backend
    private dayKeys = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

    ngOnInit() {
        this.loadSchedules();
        this.initForm();
    }

    loadSchedules() {
        this.isLoading.set(true);
        this.hhrrService.getSchedules().subscribe({
            next: (data) => {
                this.schedules.set(data);
                this.isLoading.set(false);
            },
            error: () => this.isLoading.set(false)
        });
    }

    initForm() {
        this.form = this.fb.group({
            name: ['', Validators.required],
            days: this.fb.array(this.weekDays.map((_, i) => this.createDayGroup(i < 5))) // Lunes-Viernes activos por defecto
        });
    }

    createDayGroup(isActive: boolean): FormGroup {
        return this.fb.group({
            isActive: [isActive],
            start: [isActive ? '08:00' : null],
            end: [isActive ? '17:00' : null]
        });
    }

    get daysArray() {
        return this.form.get('days') as FormArray;
    }

    copyMondayToWeek() {
    const monday = this.daysArray.at(0).value;

    if (!monday.isActive) return;

    for (let i = 1; i <= 6; i++) {
        const dayControl = this.daysArray.at(i);

        if (dayControl.value.isActive) {
            dayControl.patchValue({
                start: monday.start,
                end: monday.end
            });
        }
    }
    }

    // Generador de Texto Inteligente
    getScheduleLabel(s: WorkSchedule): { text: string, subtext: string } {
        const days = [
            { name: 'Lun', active: !!s.monday_start },
            { name: 'Mar', active: !!s.tuesday_start },
            { name: 'Mié', active: !!s.wednesday_start },
            { name: 'Jue', active: !!s.thursday_start },
            { name: 'Vie', active: !!s.friday_start },
            { name: 'Sáb', active: !!s.saturday_start },
            { name: 'Dom', active: !!s.sunday_start },
        ];

        const activeIndices = days.map((d, i) => d.active ? i : -1).filter(i => i !== -1);
        const count = activeIndices.length;

        // Caso: Nadie trabaja
        if (count === 0) return { text: 'Inactivo', subtext: 'Sin días asignados' };

        // Caso: Semana completa (Lunes a Domingo)
        if (count === 7) return { text: 'Todos los días', subtext: 'Lun - Dom' };

        // Caso: Lunes a Viernes (Estándar)
        if (count === 5 && activeIndices[0] === 0 && activeIndices[4] === 4) {
            return { text: 'Lunes a Viernes', subtext: 'Fines de semana libres' };
        }

        // Caso: Lunes a Sábado (Comercio)
        if (count === 6 && activeIndices[0] === 0 && activeIndices[5] === 5) {
            return { text: 'Lunes a Sábado', subtext: 'Domingo libre' };
        }

        // Caso: Patrón irregular (Ej: Lun, Mié, Vie)
        // Generamos una lista corta: "Lun, Mié, Vie"
        const shortList = days.filter(d => d.active).map(d => d.name).join(', ');
        return { text: 'Horario Personalizado', subtext: shortList };
    }

    onSubmit() {
        if (this.form.invalid) return;
        this.isSubmitting.set(true);

        const formVal = this.form.value;
        const payload: any = { name: formVal.name };

        // Transformar Array visual -> Objeto plano del Backend (monday_start, etc)
        formVal.days.forEach((day: any, index: number) => {
            const prefix = this.dayKeys[index];
            if (day.isActive && day.start && day.end) {
                payload[`${prefix}_start`] = `${day.start}:00`; // Asegurar formato HH:mm:ss
                payload[`${prefix}_end`] = `${day.end}:00`;
            } else {
                payload[`${prefix}_start`] = null;
                payload[`${prefix}_end`] = null;
            }
        });

        this.hhrrService.createSchedule(payload).subscribe({
            next: (res) => {
                this.schedules.update(list => [...list, res]);
                this.viewMode.set('LIST'); // Volver a lista
                this.isSubmitting.set(false);
                this.initForm(); // Reset form
            },
            error: (err) => {
                console.error(err);
                this.isSubmitting.set(false);
            }
        });
    }
}