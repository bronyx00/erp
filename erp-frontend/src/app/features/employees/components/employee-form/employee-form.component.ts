import { Component, EventEmitter, Input, Output, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { HhrrService, Employee, WorkSchedule } from '../../../../core/services/hhrr';

@Component({
  selector: 'app-employee-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './employee-form.component.html',
  host: { 
    class: 'block h-full' 
  }
})
export class EmployeeFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private hhrrService = inject(HhrrService);

  @Input() employee: Employee | null = null;
  @Output() onSave = new EventEmitter<Employee>();
  @Output() onCancel = new EventEmitter<void>();

  form!: FormGroup;
  isSubmitting = signal(false);
  schedules = signal<WorkSchedule[]>([]);

  ngOnInit() {
    this.initForm();
    this.loadSchedules();
    if (this.employee) {
      // Mapeo especial para is_active basado en el status del backend
      this.form.patchValue({
        ...this.employee,
        is_active: this.employee.status === 'Active' || this.employee.is_active
      });
      if (this.employee.emergency_contact) {
        this.form.get('emergency_contact')?.patchValue(this.employee.emergency_contact);
      }
    }
  }

  loadSchedules() {
    this.hhrrService.getSchedules().subscribe(data => this.schedules.set(data));
  }

  private initForm() {
    this.form = this.fb.group({
      first_name: ['', [Validators.required, Validators.minLength(2)]],
      last_name: ['', [Validators.required, Validators.minLength(2)]],
      identification: ['', [Validators.required]], 
      email: ['', [Validators.required, Validators.email]],
      phone: [''],
      address: ['', Validators.required],        
      birth_date: ['', Validators.required], 

      position: ['', Validators.required],
      department: ['', Validators.required],
      salary: [0, [Validators.required, Validators.min(0)]],
      hired_at: [new Date().toISOString().split('T')[0], Validators.required],
      
      contract_type: ['UNDEFINED'],
      bonus_scheme: ['Standard'],
      schedule_id: [null],
      
      // Contacto Emergencia 
      emergency_contact: this.fb.group({
        name: [''],
        phone: [''],
        relationship: ['']
      }),

      is_active: [true] // Checkbox visual
    });
  }

  onSubmit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);
    const formVal = this.form.value;

    const payload: any = {
      first_name: formVal.first_name,
      last_name: formVal.last_name,
      identification: formVal.identification,
      email: formVal.email,
      phone: formVal.phone || "N/A",
      address: formVal.address,
      birth_date: formVal.birth_date,
      position: formVal.position,
      department: formVal.department,
      manager_id: 0, // Backend lo convierte a None
      hired_at: formVal.hired_at,
      schedule_id: formVal.schedule_id ? Number(formVal.schedule_id) : 0, // Backend lo convierte a None
      contract_type: formVal.contract_type,
      salary: Number(formVal.salary), // Asegurar numérico
      bonus_scheme: formVal.bonus_scheme,
      
      // Objetos y Listas obligatorias por schema
      documents: [],
      performance_reviews: [], 
      emergency_contact: {
          name: formVal.emergency_contact?.name || "N/A",
          phone: formVal.emergency_contact?.phone || "N/A",
          relationship: formVal.emergency_contact?.relationship || "N/A"
      },
      status: formVal.is_active ? 'Active' : 'Inactive'
    };

    const request$ = this.employee 
      ? this.hhrrService.updateEmployee(this.employee.id, payload)
      : this.hhrrService.createEmployee(payload);

    request$.subscribe({
      next: (res) => {
        this.isSubmitting.set(false);
        this.onSave.emit(res);
      },
      error: (err) => {
        console.error('Error saving employee', err);
        this.isSubmitting.set(false);
        alert('Error al guardar. Verifica los datos.');
      }
    });
  }
}