import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { HhrrService, Employee } from '../../core/services/hhrr';

@Component({
  selector: 'app-employees',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './employees.html',
  styleUrl: './employees.scss',
})
export class EmployeesComponent implements OnInit {
  private hhrrService = inject(HhrrService);
  private fb = inject(FormBuilder);

  employees = signal<Employee[]>([]);
  isSubmitting = false;
  errorMessage = '';

  employeeForm = this.fb.group({
    first_name: ['', [Validators.required]],
    last_name: ['', [Validators.required]],
    identification: ['', [Validators.required]],
    phone: [''],
    position: ['Vendedor', [Validators.required]],
    salary: [0, [Validators.required, Validators.min(0)]],
    email: ['', [Validators.email]],
    hired_at: [new Date().toISOString().split('T')[0], [Validators.required]]
  });

  ngOnInit() {
    this.loadEmployees();
  }

  loadEmployees() {
    this.hhrrService.getEmployees().subscribe({
      next: (data) => this.employees.set(data),
      error: (e) => console.error('Error cargando empleados', e)
    });
  }

  onSubmit() {
    if (this.employeeForm.valid) {
      this.isSubmitting = true;
      this.errorMessage = '';

      const val = this.employeeForm.value;

      const newEmp: Employee = {
        first_name: val.first_name!,
        last_name: val.last_name!,
        identification: val.identification || '',
        email: val.email || '',
        phone: val.phone || undefined,

        position: val.position || 'Vendedor',
        salary: Number(val.salary),
        hired_at: val.hired_at || undefined,
        is_active: true
      };

      this.hhrrService.createEmployee(newEmp).subscribe({
        next: (emp) => {
          this.employees.update(list => [...list, emp]);
          this.isSubmitting = false;

          // Reset parcial manteniendo la fecha
          this.employeeForm.reset({
            position: 'Vendedor',
            salary: 0,
            hired_at: new Date().toISOString().split('T')[0]
          });
          alert('Empleado registrado exitosamente');
        },
        error: (e) => {
          console.error(e);
          this.isSubmitting = false;
          const detail = e.error?.detail;
          
          if (Array.isArray(detail)) {
            this.errorMessage = detail.map((err: any) => `${err.loc.join('.')}: ${err.msg}`).join(', ');
          } else {
            this.errorMessage = detail || 'Error al guardar. Verifica los datos.'
          }
        }
      });
    }
  }
}
