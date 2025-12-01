import { Component, inject, ElementRef, ViewChild, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { InventoryService, ProductCreate } from '../../../core/services/inventory';
import { Router } from '@angular/router';

@Component({
  selector: 'app-product-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './product-form.html',
  styleUrl: './product-form.scss',
})
export class ProductFormComponent {
  private inventoryService = inject(InventoryService);
  private fb = inject(FormBuilder);
  private router = Inject(Router);

  @ViewChild('skuInput') skuInput!: ElementRef;

  isSubmitting = false;
  lastProductSaved: string | null = null;

  productForm = this.fb.group({
    sku: ['', Validators.required],
    name: ['', Validators.required],
    description: [''],
    price: [0, [Validators.required, Validators.min(0.01)]],
    stock: [0, [Validators.required, Validators.min(0)]]
  });

  onSubmit() {
    if (this.productForm.valid) {
      this.isSubmitting = true;
      const newProd = this.productForm.value as ProductCreate;

      this.inventoryService.createProduct(newProd).subscribe({
        next: (res) => {
          this.lastProductSaved = `${res.name} (SKU: ${res.sku})`;
          this.isSubmitting = false;

          // Reiniciar formulario para el siguiente producto INMEDIATAMENTE
          this.productForm.reset({
            sku: '',
            name: '',
            description: '',
            price: 0,
            stock: 0
          });

          // Re-enfocar el primer campo
          setTimeout(() => this.skuInput.nativeElement.focus(), 100);
        },
        error: (err) => {
          alert('Error al guardar producto');
          this.isSubmitting = false;
        }
      });
    }
  }

  goBack() {
    this.router.navigate(['/dashboard']);
  }
}
