import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators, AbstractControl } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './register.component.html'
})
export class RegisterComponent {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private router = inject(Router);

  isLoading = signal(false);
  step = signal(1); // 1: Datos Personales, 2: Datos Empresa

  form = this.fb.group({
    // Paso 1: Usuario
    full_name: ['', [Validators.required, Validators.minLength(3)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
    confirmPassword: ['', [Validators.required]],
    
    // Paso 2: Empresa (Tenant)
    company_name: ['', [Validators.required]], // Nombre comercial
    company_business_name: ['', [Validators.required]], // Razón social
    company_rif: ['', [Validators.required]],
    company_address: ['', [Validators.required]]
  }, { validators: this.passwordMatchValidator });

  passwordMatchValidator(g: AbstractControl) {
    return g.get('password')?.value === g.get('confirmPassword')?.value 
      ? null : { mismatch: true };
  }

  nextStep() {
    // Validar campos del paso 1 antes de avanzar
    const controls = ['full_name', 'email', 'password', 'confirmPassword'];
    const invalid = controls.some(c => this.form.get(c)?.invalid);
    
    if (invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.step.set(2);
  }

  prevStep() {
    this.step.set(1);
  }

  onSubmit() {
    if (this.form.invalid) return;

    this.isLoading.set(true);
    const { confirmPassword, ...payload } = this.form.value;

    this.authService.register(payload).subscribe({
      next: () => {
        alert('✅ ¡Cuenta creada con éxito!\nAhora puedes iniciar sesión.');
        this.router.navigate(['/login']);
      },
      error: (err) => {
        console.error(err);
        this.isLoading.set(false);
        alert(err.error?.detail || 'Error al registrar cuenta.');
      }
    });
  }
}