import { Component, EventEmitter, Output, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { UsersService } from '../../../../core/services/users';

@Component({
  selector: 'app-user-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './user-form.component.html'
})
export class UserFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private userService = inject(UsersService);

  @Output() onSave = new EventEmitter<void>();
  @Output() onCancel = new EventEmitter<void>();

  form: FormGroup;
  isLoading = signal(false);
  availableEmployees = signal<any[]>([]); // Lista cruda de empleados

  constructor() {
    this.form = this.fb.group({
      full_name: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      role: ['SALES_AGENT', Validators.required],
      password: ['', [Validators.required, Validators.minLength(6)]]
    });
  }

  ngOnInit() {
    // Cargamos empleados para el select
    this.userService.getEmployeesForLinking().subscribe(emps => {
      this.availableEmployees.set(emps);
    });
  }

  onEmployeeSelect(event: Event) {
    const select = event.target as HTMLSelectElement;
    const id = parseInt(select.value);
    const emp = this.availableEmployees().find(e => e.id === id);
    
    if (emp) {
        this.form.patchValue({
            full_name: `${emp.first_name} ${emp.last_name}`,
            email: emp.email
        });
    }
  }

  submit() {
    if (this.form.invalid) return;
    this.isLoading.set(true);
    
    this.userService.createUser(this.form.value).subscribe({
        next: () => {
            this.isLoading.set(false);
            this.onSave.emit();
        },
        error: (err) => {
            console.error(err);
            alert('Error al crear usuario. Verifica que el email no esté duplicado.');
            this.isLoading.set(false);
        }
    });
  }

  // Helper para el template HTML
  get role() {
      return this.form.get('role')?.value;
  }
}