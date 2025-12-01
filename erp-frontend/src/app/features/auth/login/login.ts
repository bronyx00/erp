import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="login-container">
      <div class="login-card">
        <h2>ERP Next-Gen</h2>
        <p>Ingresa a tu cuenta empresarial</p>

        <form [formGroup]="loginForm" (ngSubmit)="onSubmit()">
          
          <div class="form-group">
            <label for="email">Correo Electrónico</label>
            <input id="email" type="email" formControlName="email" placeholder="admin@miempresa.com">
          </div>

          <div class="form-group">
            <label for="password">Contraseña</label>
            <input id="password" type="password" formControlName="password" placeholder="********">
          </div>

          @if (errorMessage) {
            <div class="error-message">
              {{ errorMessage }}
            </div>
          }

          <button type="submit" [disabled]="loginForm.invalid || isLoading">
            {{ isLoading ? 'Entrando...' : 'Iniciar Sesión' }}
          </button>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .login-container {
      display: flex; justify-content: center; align-items: center;
      height: 100vh; background-color: #f3f4f6;
    }
    .login-card {
      background: white; padding: 2rem; border-radius: 8px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 400px;
    }
    .form-group { margin-bottom: 1rem; }
    input {
      width: 100%; padding: 0.5rem; margin-top: 0.25rem;
      border: 1px solid #d1d5db; border-radius: 4px;
    }
    button {
      width: 100%; padding: 0.75rem; background-color: #2563eb;
      color: white; border: none; border-radius: 4px; cursor: pointer;
      font-weight: bold;
    }
    button:disabled { background-color: #93c5fd; }
    .error-message { color: #dc2626; margin-bottom: 1rem; font-size: 0.875rem; }
  `]
})
export class LoginComponent {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private router = inject(Router);

  loginForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]]
  });

  isLoading = false;
  errorMessage = '';

  onSubmit() {
    if (this.loginForm.valid) {
      this.isLoading = true;
      this.errorMessage = '';
      
      const { email, password } = this.loginForm.value;

      this.authService.login(email!, password!).subscribe({
        next: () => {
          const role = this.authService.currentUserRole();
          if (role === 'CASHIER') {
            this.router.navigate(['/pos']);
          } else {
            this.router.navigate(['/dashboard']);
          }
        },
        error: (err) => {
          this.isLoading = false;
          if (err.status === 401) {
            this.errorMessage = 'Credenciales incorrectas.';
          } else {
            this.errorMessage = 'Error de conexión con el servidor.';
          }
          console.error(err);
        }
      });
    }
  }
}