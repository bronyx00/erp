import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validator, Validators } from '@angular/forms';
import { UsersService, User } from '../../core/services/users';

@Component({
  selector: 'app-team',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './team.html',
  styleUrl: './team.scss',
})
export class TeamComponent implements OnInit {
  private usersService = inject(UsersService);
  private fb = inject(FormBuilder);

  users = signal<User[]>([]);
  isSubmitting = false;

  userForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(5)]],
    role: ['CASHIER', [Validators.required]]
  });

  ngOnInit() {
    this.loadUser();
  }
  
  loadUser() {
    this.usersService.getEmployees().subscribe({
      next: (data) => this.users.set(data),
      error: (err) => console.error('Error cargando usuarios', err)
    });
  }

  onSubmit() {
    if (this.userForm.valid) {
      this.isSubmitting = true;
      const newUser = this.userForm.value as User;

      this.usersService.createEmployee(newUser).subscribe({
        next: (createdUser) => {
          this.users.update(list => [...list, createdUser]);
          this.isSubmitting = false;
          this.userForm.reset({ role: 'CASHIER' });
          alert('Empleado creado con éxito');
        },
        error: (err) => {
          this.isSubmitting = false;
          alert('Error creando usuario: ' + (err.error?.detail || 'Error desconocido.'));
        }
      });
    }
  }
}
