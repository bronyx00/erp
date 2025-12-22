import { Component, EventEmitter, Input, Output, OnInit, inject, effect, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { CrmService } from '../services/crm.service';
import { Customer, CustomerPayload } from '../models/customer.model';

@Component({
  selector: 'app-client-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './client-form.component.html'
})
export class ClientFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private crmService = inject(CrmService);

  // --- INPUTS & OUTPUTS ---
  // Recibimos el cliente si estamos editando (o null si es nuevo)
  @Input() set customer(value: Customer | null) {
    this._customer.set(value);
  }
  
  // Emitimos evento al terminar para que el padre cierre el drawer y recargue
  @Output() onSave = new EventEmitter<void>();
  @Output() onCancel = new EventEmitter<void>();

  // --- STATE ---
  private _customer = signal<Customer | null>(null);
  isLoading = this.crmService.isLoading;
  form!: FormGroup;
  isEditMode = signal(false);

  constructor() {
    this.initForm();

    // Effect: Reacciona cuando cambia el cliente seleccionado (Input)
    effect(() => {
      const currentCustomer = this._customer();
      if (currentCustomer) {
        this.isEditMode.set(true);
        this.form.patchValue({
          name: currentCustomer.name,
          email: currentCustomer.email,
          taxId: currentCustomer.taxId,
          phone: currentCustomer.phone,
          address: currentCustomer.address
        });
      } else {
        this.isEditMode.set(false);
        this.form.reset();
      }
    });
  }

  ngOnInit() {}

  private initForm() {
    this.form = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(3)]],
      email: ['', [Validators.email]], // Opcional pero debe ser válido
      taxId: ['', [Validators.required]], // RIF/CUIT
      phone: [''],
      address: ['']
    });
  }

  onSubmit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched(); // Muestra errores rojos si el usuario intenta guardar incompleto
      return;
    }

    const formValue = this.form.value;

    // ADAPTER: Transformamos camelCase (Form) a snake_case (API Payload)
    const payload: CustomerPayload = {
      name: formValue.name,
      email: formValue.email || null,
      tax_id: formValue.taxId,
      phone: formValue.phone || null,
      address: formValue.address || null
    };

    const request$ = this.isEditMode() 
      ? this.crmService.updateCustomer(this._customer()!.id, payload)
      : this.crmService.createCustomer(payload);

    request$.subscribe({
      next: () => {
        this.onSave.emit(); // ¡Éxito! Avisamos al padre
        this.form.reset();
      },
      error: (err) => console.error('Error saving customer', err)
    });
  }
}