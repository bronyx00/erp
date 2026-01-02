import { Component, EventEmitter, Input, Output, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Account } from '../../models/accounting.models';
import { AccountingService } from '../../services/accounting.service';

@Component({
  selector: 'app-account-form-modal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" (click)="close.emit()"></div>

      <div class="relative w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95">
        <div class="px-6 py-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
          <h3 class="text-lg font-bold text-slate-800">
            {{ isEditMode ? 'Editar Cuenta' : 'Nueva Cuenta' }}
          </h3>
          <button (click)="close.emit()" class="text-slate-400 hover:text-rose-500"><i class="fas fa-times"></i></button>
        </div>

        <form [formGroup]="form" (ngSubmit)="save()" class="p-6 space-y-4">
          
          <div *ngIf="parentAccount && !isEditMode" class="p-3 bg-blue-50 rounded-lg border border-blue-100 text-sm text-blue-800 mb-2">
            <span class="font-bold">Cuenta Padre:</span> {{ parentAccount.code }} - {{ parentAccount.name }}
          </div>

          <div *ngIf="!parentAccount && !isEditMode">
            <label class="block text-xs font-bold text-slate-500 uppercase mb-1">Ubicación (Cuenta Padre)</label>
            <select formControlName="parent_id" (change)="onParentChange()" 
                    class="w-full rounded-lg border-slate-300 text-sm focus:ring-indigo-500">
              <option [ngValue]="null" disabled>Seleccione donde ubicarla...</option>
              @for (acc of potentialParents(); track acc.id) {
                <option [value]="acc.id">{{ acc.code }} - {{ acc.name }}</option>
              }
            </select>
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-500 uppercase mb-1">Código</label>
            <div class="flex items-center gap-2">
               <span *ngIf="!isEditMode && selectedParentCode()" class="text-slate-400 font-mono">{{ selectedParentCode() }}.</span>
               
               <input formControlName="code_suffix" type="text" 
                      class="flex-1 rounded-lg border-slate-300 focus:ring-indigo-500" 
                      [readonly]="isEditMode"
                      placeholder="Ej: 005">
            </div>
            <p *ngIf="!isEditMode" class="text-[10px] text-slate-400 mt-1">El código final será {{ getFullCode() }}</p>
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-500 uppercase mb-1">Nombre</label>
            <input formControlName="name" type="text" class="w-full rounded-lg border-slate-300 focus:ring-indigo-500">
          </div>

          <div class="pt-4 flex justify-end gap-3">
            <button type="button" (click)="close.emit()" class="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg text-sm font-medium">Cancelar</button>
            <button type="submit" [disabled]="form.invalid || isLoading" class="px-6 py-2 bg-indigo-600 text-white rounded-lg text-sm font-bold hover:bg-indigo-700 disabled:opacity-50">
              {{ isLoading ? 'Guardando...' : 'Guardar' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  `
})
export class AccountFormModalComponent implements OnInit {
  @Input() parentAccount: Account | null = null;
  @Input() accountToEdit: Account | null = null; // Si viene, es modo edición
  @Output() close = new EventEmitter<void>();
  @Output() saved = new EventEmitter<void>();

  private fb = inject(FormBuilder);
  private service = inject(AccountingService);

  form: FormGroup;
  isLoading = false;
  isEditMode = false;

  // Lista de posibles padres 
  potentialParents = signal<Account[]>([]);
  selectedParentCode = signal<string>('');

  constructor() {
    this.form = this.fb.group({
      parent_id: [null],
      code_suffix: ['', [Validators.required, Validators.pattern(/^[0-9.]+$/)]],
      name: ['', Validators.required]
    });
  }

  ngOnInit() {
    if (this.accountToEdit) {
      this.isEditMode = true;
      this.form.patchValue({
        code_suffix: this.accountToEdit.code,
        name: this.accountToEdit.name
      });
      this.form.get('code_suffix')?.disable();
    } 
    else if (this.parentAccount) {
      // Modo "Agregar Hija" (Directo)
      this.selectedParentCode.set(this.parentAccount.code);
      this.form.get('parent_id')?.setValue(this.parentAccount.id);
    } 
    else {
      // Modo "Global" -> Cargar lista de padres
      this.loadParents();
    }
  }

  loadParents() {
    this.service.getAccounts().subscribe(accounts => {
      // Solo cuentas carpeta (no transaccionales)
      const folders = accounts.filter(a => !a.is_transactional);
      this.potentialParents.set(folders);
    });
  }

  onParentChange() {
    const parentId = Number(this.form.get('parent_id')?.value);
    const parent = this.potentialParents().find(p => p.id === parentId);
    if (parent) {
      this.selectedParentCode.set(parent.code);
    }
  }

  getFullCode(): string {
    const suffix = this.form.get('code_suffix')?.value || '';
    if (this.isEditMode) return suffix;
    return this.parentAccount ? `${this.parentAccount.code}.${suffix}` : suffix;
  }

  save() {
    if (this.form.invalid) return;
    this.isLoading = true;

    if (this.isEditMode && this.accountToEdit) {
      // UPDATE (Igual que antes)
      this.service.updateAccount(this.accountToEdit.id, {
        name: this.form.get('name')?.value,
        is_active: true
      }).subscribe({
        next: () => this.finish(),
        error: (e) => this.handleError(e)
      });
    } else {
      // CREATE
      // Necesitamos el objeto padre completo para saber el account_type
      const parentId = this.parentAccount?.id || this.form.get('parent_id')?.value;
      
      // Buscar el objeto padre para heredar el tipo (ASSET, LIABILITY...)
      let parentObj = this.parentAccount;
      if (!parentObj) {
         parentObj = this.potentialParents().find(p => p.id == parentId) || null;
      }

      if (!parentObj) {
        this.handleError({ error: { detail: "Debes seleccionar una cuenta padre obligatoriamente." }});
        return;
      }

      const newAccount = {
        code: this.getFullCode(),
        name: this.form.get('name')?.value,
        account_type: parentObj.account_type, // Heredar tipo del padre
        parent_id: Number(parentId),
        is_transactional: true // Por defecto creamos hojas
      };
      
      this.service.createAccount(newAccount).subscribe({
        next: () => this.finish(),
        error: (e) => this.handleError(e)
      });
    }
  }

  finish() {
    this.isLoading = false;
    this.saved.emit();
    this.close.emit();
  }

  handleError(err: any) {
    this.isLoading = false;
    alert("Error: " + (err.error?.detail || "No se pudo guardar"));
  }
}