import { Component, EventEmitter, Input, Output, inject, effect, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { InventoryService } from '../services/inventory.service';
import { Product, ProductPayload } from '../models/product.model';

@Component({
    selector: 'app-product-form',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule],
    templateUrl: './product-form.component.html'
})
export class ProductFormComponent {
    private fb = inject(FormBuilder);
    private inventoryService = inject(InventoryService);

    @Input() set product(value: Product | null) {
        this._product.set(value);
    }

    @Output() onSave = new EventEmitter<void>();
    @Output() onCancel = new EventEmitter<void>();

    private _product = signal<Product | null>(null);
    isLoading = this.inventoryService.isLoading;
    form!: FormGroup;
    isEditMode = signal(false);

    // Opciones para el select
    unitOptions = [
        { value: 'UNIT', label: 'Unidad / Pieza' },
        { value: 'KG', label: 'Kilogramos (KG)' },
        { value: 'METER', label: 'Metros (M)' },
        { value: 'LITER', label: 'Litros (L)' },
        { value: 'SERVICE', label: 'Servicio / Horas' }
    ];

    constructor() {
        this.initForm();

        effect(() => {
            const p = this._product();
            if (p) {
                this.isEditMode.set(true);
                this.form.patchValue({
                name: p.name,
                sku: p.sku,
                category: p.category,
                measurementUnit: p.measurementUnit,
                price: p.price,
                stock: p.stock,
                description: p.description
                });
                // Deshabilitar SKU en edición para evitar inconsistencias
                this.form.get('sku')?.disable(); 
            } else {
                this.isEditMode.set(false);
                this.form.reset({ 
                    stock: 0, 
                    category: 'General',
                    measurementUnit: 'UNIT',
                    price: 0
                });
                this.form.get('sku')?.enable();
            }
        });
    }

    private initForm() {
        this.form = this.fb.group({
            name: ['', [Validators.required, Validators.minLength(3)]],
            sku: ['', [Validators.required]],
            category: ['General', [Validators.required]],
            measurementUnit: ['UNIT', [Validators.required]],
            price: [0, [Validators.required, Validators.min(0.01)]],
            stock: [0, [Validators.required, Validators.min(0)]],
            description: ['']
        });
    }

    onSubmit() {
        if (this.form.invalid) {
            this.form.markAllAsTouched();
            return;
        }

        const val = this.form.getRawValue();
        const payload: ProductPayload = {
            name: val.name,
            sku: val.sku,
            category: val.category || 'General',
            measurement_unit: val.measurementUnit, // Enviamos al backend
            price: val.price,
            stock: val.stock,
            description: val.description || null
        };

        const req$ = this.isEditMode()
        ? this.inventoryService.updateProduct(this._product()!.id, payload)
        : this.inventoryService.createProduct(payload);

        req$.subscribe({
            next: () => {
                this.onSave.emit();
                this.form.reset(); 
            },
            error: (err) => {
                console.error('Error saving product', err);
                // Aquí podrías manejar el error 400 de "SKU duplicado"
                if (err.status === 400) {
                    this.form.get('sku')?.setErrors({ duplicate: true });
                }
            }
        });
    }
}