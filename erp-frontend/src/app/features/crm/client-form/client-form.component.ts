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

  @Input() set customer(value: Customer | null) {
    this._customer.set(value);
  }
  
  // Nuevo Input para pre-llenar la cédula
  @Input() set initialTaxId(value: string | null) {
    if (value && !this.isEditMode()) {
      this.form.patchValue({ taxId: value });
    }
  }

  @Output() onSave = new EventEmitter<Customer>(); // Emitimos el cliente creado
  @Output() onCancel = new EventEmitter<void>();

  private _customer = signal<Customer | null>(null);
  isLoading = this.crmService.isLoading;
  form!: FormGroup;
  isEditMode = signal(false);

  constructor() {
    this.initForm();

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
      email: ['', [Validators.email]],
      taxId: ['', [Validators.required]],
      phone: [''],
      address: ['']
    });
  }

  onSubmit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const formValue = this.form.value;
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
      next: (customer) => {
        this.onSave.emit(customer); // Devolvemos el cliente al padre
        this.form.reset();
      },
      error: (err) => console.error('Error saving customer', err)
    });
  }
}