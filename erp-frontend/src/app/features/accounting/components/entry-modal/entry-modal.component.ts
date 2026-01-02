// features/accounting/components/entry-modal/entry-modal.component.ts
import { Component, EventEmitter, Output, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { AccountingService } from '../../services/accounting.service';
import { Account, EntryTemplate, LedgerEntryCreate, LedgerLineCreate } from '../../models/accounting.models';

@Component({
  selector: 'app-entry-modal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule],
  template: `
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity" (click)="close.emit()"></div>

      <div class="relative w-full max-w-4xl bg-white rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden animate-in zoom-in-95 duration-200">
        
        <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <div>
            <h3 class="text-lg font-bold text-slate-800">Registrar Operación Contable</h3>
            <p class="text-xs text-slate-500">Selecciona una plantilla rápida o usa el modo avanzado.</p>
          </div>
          <button (click)="close.emit()" class="text-slate-400 hover:text-rose-500 transition">
            <i class="fas fa-times text-xl"></i>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-6 bg-white">
          
          <div class="flex gap-4 mb-6 border-b border-slate-100">
            <button (click)="mode.set('template')" 
                    [class]="mode() === 'template' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-slate-500 hover:text-slate-700'"
                    class="pb-2 text-sm font-semibold transition-colors flex items-center gap-2">
              <i class="fas fa-magic"></i> Plantillas (Rápido)
            </button>
            <button (click)="mode.set('manual')"
                    [class]="mode() === 'manual' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-slate-500 hover:text-slate-700'"
                    class="pb-2 text-sm font-semibold transition-colors flex items-center gap-2">
              <i class="fas fa-list-ol"></i> Avanzado (Manual)
            </button>
          </div>

          <div *ngIf="mode() === 'template'" class="space-y-6">
            
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              @for (tpl of templates(); track tpl.id) {
                <div (click)="selectTemplate(tpl)"
                     [class.ring-2]="selectedTemplate()?.id === tpl.id"
                     [class.ring-indigo-500]="selectedTemplate()?.id === tpl.id"
                     class="cursor-pointer border border-slate-200 rounded-xl p-4 hover:shadow-md transition bg-slate-50 hover:bg-white group">
                  <div class="flex items-start gap-3">
                    <div class="h-8 w-8 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center shrink-0">
                      <i class="fas fa-bolt text-sm"></i>
                    </div>
                    <div>
                      <h4 class="font-bold text-slate-700 text-sm group-hover:text-indigo-700">{{ tpl.name }}</h4>
                      <p class="text-xs text-slate-500 mt-1 leading-relaxed">{{ tpl.description }}</p>
                    </div>
                  </div>
                </div>
              }
            </div>

            <div *ngIf="selectedTemplate()" class="mt-6 p-5 bg-slate-50 rounded-xl border border-slate-200 animate-in slide-in-from-top-2">
              <h4 class="font-bold text-slate-700 mb-4 flex items-center gap-2">
                <i class="fas fa-pen-to-square"></i> Completar Datos
              </h4>
              
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                @for (field of selectedTemplate()!.fields; track field.key) {
                  <div>
                    <label class="block text-xs font-semibold text-slate-500 uppercase mb-1">
                      {{ field.label }} <span *ngIf="field.required" class="text-rose-500">*</span>
                    </label>
                    
                    <input *ngIf="field.type === 'number'" 
                           type="number" 
                           [(ngModel)]="templateData[field.key]"
                           class="w-full rounded-lg border-slate-300 text-sm focus:ring-indigo-500 focus:border-indigo-500 py-2">
                    
                    <input *ngIf="field.type === 'text'" 
                           type="text" 
                           [(ngModel)]="templateData[field.key]"
                           class="w-full rounded-lg border-slate-300 text-sm focus:ring-indigo-500 focus:border-indigo-500 py-2">

                    <select *ngIf="field.type === 'select'"
                            [(ngModel)]="templateData[field.key]"
                            class="w-full rounded-lg border-slate-300 text-sm focus:ring-indigo-500 focus:border-indigo-500 py-2 bg-white">
                      <option [ngValue]="undefined" disabled>Seleccione...</option>
                      @for (opt of field.options; track opt.value) {
                        <option [value]="opt.value">{{ opt.label }}</option>
                      }
                    </select>

                  </div>
                }
              </div>

              <div class="mt-4 flex justify-end">
                <button (click)="previewTemplateEntry()" 
                        [disabled]="isLoading()"
                        class="bg-slate-800 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-900 transition flex items-center gap-2">
                  <span *ngIf="isLoading()" class="fas fa-spinner fa-spin"></span>
                  Generar Asiento
                </button>
              </div>
            </div>
          </div>

          <div *ngIf="mode() === 'manual' || entryForm.get('lines')?.value.length > 0" 
               [class.mt-8]="mode() === 'template'"
               class="animate-in fade-in">
            
            <form [formGroup]="entryForm">
              
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div>
                  <label class="block text-xs font-bold text-slate-500 uppercase mb-1">Fecha</label>
                  <input type="date" formControlName="transaction_date" class="w-full rounded-lg border-slate-300 text-sm focus:ring-indigo-500">
                </div>
                <div class="md:col-span-2">
                  <label class="block text-xs font-bold text-slate-500 uppercase mb-1">Descripción General</label>
                  <input type="text" formControlName="description" class="w-full rounded-lg border-slate-300 text-sm focus:ring-indigo-500" placeholder="Ej: Pago de alquiler mes actual">
                </div>
              </div>

              <div class="border border-slate-200 rounded-lg overflow-hidden mb-4">
                <table class="w-full text-sm">
                  <thead class="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                    <tr>
                      <th class="px-4 py-2 text-left w-1/2">Cuenta Contable</th>
                      <th class="px-4 py-2 text-right w-1/4">Débito</th>
                      <th class="px-4 py-2 text-right w-1/4">Crédito</th>
                      <th class="w-10"></th>
                    </tr>
                  </thead>
                  <tbody formArrayName="lines">
                    <tr *ngFor="let line of linesControls.controls; let i = index" [formGroupName]="i" class="border-b border-slate-50 last:border-0">
                      
                      <td class="p-2">
                        <select formControlName="account_id" class="w-full border-none bg-transparent focus:ring-0 text-sm font-medium text-slate-700">
                          <option [ngValue]="null">Seleccionar Cuenta...</option>
                          <option *ngFor="let acc of transactionalAccounts()" [value]="acc.id">
                            {{ acc.code }} - {{ acc.name }}
                          </option>
                        </select>
                      </td>

                      <td class="p-2">
                        <input type="number" formControlName="debit" 
                               (change)="onAmountChange(i, 'debit')"
                               class="w-full text-right border-slate-200 rounded text-sm py-1 focus:ring-indigo-500 placeholder-slate-300" placeholder="0.00">
                      </td>

                      <td class="p-2">
                        <input type="number" formControlName="credit" 
                               (change)="onAmountChange(i, 'credit')"
                               class="w-full text-right border-slate-200 rounded text-sm py-1 focus:ring-indigo-500 placeholder-slate-300" placeholder="0.00">
                      </td>

                      <td class="p-2 text-center">
                        <button (click)="removeLine(i)" class="text-slate-300 hover:text-rose-500 transition">
                          <i class="fas fa-trash-alt"></i>
                        </button>
                      </td>
                    </tr>
                  </tbody>
                  <tfoot class="bg-slate-50 font-bold text-slate-700">
                    <tr>
                      <td class="px-4 py-2 text-right uppercase text-xs tracking-wider">Totales</td>
                      <td class="px-4 py-2 text-right" [class.text-rose-600]="!isBalanced()">
                        {{ totalDebit() | number:'1.2-2' }}
                      </td>
                      <td class="px-4 py-2 text-right" [class.text-rose-600]="!isBalanced()">
                        {{ totalCredit() | number:'1.2-2' }}
                      </td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
              
              <div class="flex justify-between items-center">
                <button (click)="addLine()" class="text-indigo-600 hover:text-indigo-800 text-sm font-semibold flex items-center gap-2">
                  <i class="fas fa-plus-circle"></i> Agregar Línea
                </button>

                <div *ngIf="!isBalanced()" class="text-rose-600 text-xs font-bold bg-rose-50 px-3 py-1 rounded-full animate-pulse">
                  <i class="fas fa-exclamation-triangle mr-1"></i> 
                  Asiento Descuadrado (Dif: {{ (totalDebit() - totalCredit()) | number:'1.2-2' }})
                </div>
              </div>

            </form>
          </div>
        </div>

        <div class="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-3">
          <button (click)="close.emit()" class="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg text-sm font-medium transition">
            Cancelar
          </button>
          
          <button (click)="saveEntry()" 
                  [disabled]="isLoading() || !isValidEntry()"
                  [class.opacity-50]="!isValidEntry()"
                  class="px-6 py-2 bg-indigo-600 text-white rounded-lg text-sm font-bold hover:bg-indigo-700 transition shadow-lg shadow-indigo-200 flex items-center gap-2">
            <span *ngIf="isLoading()" class="fas fa-spinner fa-spin"></span>
            Confirmar y Contabilizar
          </button>
        </div>

      </div>
    </div>
  `
})
export class EntryModalComponent implements OnInit {
  @Output() close = new EventEmitter<void>();
  @Output() entryCreated = new EventEmitter<void>();

  private fb = inject(FormBuilder);
  private accountingService = inject(AccountingService);
  
  mode = signal<'template' | 'manual'>('template');
  isLoading = signal(false);
  
  templates = signal<EntryTemplate[]>([]);
  transactionalAccounts = signal<Account[]>([]);
  
  selectedTemplate = signal<EntryTemplate | null>(null);
  templateData: Record<string, any> = {};

  entryForm: FormGroup;

  constructor() {
    this.entryForm = this.fb.group({
      transaction_date: [new Date().toISOString().substring(0, 10), Validators.required],
      description: ['', Validators.required],
      reference: [''],
      lines: this.fb.array([])
    });
  }

  ngOnInit() {
    this.loadInitialData();
  }

  get linesControls() {
    return this.entryForm.get('lines') as FormArray;
  }

  loadInitialData() {
    this.isLoading.set(true);
    Promise.all([
      new Promise(resolve => this.accountingService.getTemplates().subscribe(t => { this.templates.set(t); resolve(true); })),
      new Promise(resolve => this.accountingService.getAccounts(true).subscribe(a => { this.transactionalAccounts.set(a); resolve(true); }))
    ]).finally(() => this.isLoading.set(false));
  }

  selectTemplate(tpl: EntryTemplate) {
    this.selectedTemplate.set(tpl);
    this.templateData = {}; 
  }

  previewTemplateEntry() {
    if (!this.selectedTemplate()) return;
    
    this.isLoading.set(true);
    const request = {
      template_id: this.selectedTemplate()!.id,
      data: this.templateData
    };

    this.accountingService.previewTemplate(request).subscribe({
      next: (entryStruct) => {
        this.entryForm.patchValue({
          transaction_date: entryStruct.transaction_date,
          description: entryStruct.description,
          reference: entryStruct.reference
        });
        
        this.linesControls.clear();
        entryStruct.lines.forEach(line => {
          this.linesControls.push(this.createLineGroup(line));
        });

        this.isLoading.set(false);
      },
      error: (err) => {
        console.error(err);
        this.isLoading.set(false);
        const msg = err.error?.detail || "Verifique los datos (monto o cuenta)";
        alert(`Error: ${msg}`);
      }
    });
  }

  createLineGroup(data?: LedgerLineCreate) {
    return this.fb.group({
      account_id: [data?.account_id || null, Validators.required],
      debit: [data?.debit || 0, [Validators.min(0)]],
      credit: [data?.credit || 0, [Validators.min(0)]]
    });
  }

  addLine() {
    this.linesControls.push(this.createLineGroup());
  }

  removeLine(index: number) {
    this.linesControls.removeAt(index);
  }

  onAmountChange(index: number, field: 'debit' | 'credit') {
    const line = this.linesControls.at(index);
    // IMPORTANTE: Asegurar que el valor se trate como número al evaluar
    const val = Number(line.get(field)?.value || 0);
    
    if (field === 'debit' && val > 0) {
      line.patchValue({ credit: 0 }, { emitEvent: false });
    } else if (field === 'credit' && val > 0) {
      line.patchValue({ debit: 0 }, { emitEvent: false });
    }
  }

  // --- CORRECCIÓN CLAVE: Sumar Números, NO Concatenar Strings ---
  totalDebit(): number {
    return this.linesControls.controls
      .map(c => Number(c.get('debit')?.value || 0)) // <-- Number() Wrapper
      .reduce((a, b) => a + b, 0);
  }

  totalCredit(): number {
    return this.linesControls.controls
      .map(c => Number(c.get('credit')?.value || 0)) // <-- Number() Wrapper
      .reduce((a, b) => a + b, 0);
  }

  isBalanced(): boolean {
    return Math.abs(this.totalDebit() - this.totalCredit()) < 0.01 && this.totalDebit() > 0;
  }

  isValidEntry(): boolean {
    return this.entryForm.valid && this.isBalanced() && this.linesControls.length > 0;
  }

  saveEntry() {
    if (!this.isValidEntry()) return;

    this.isLoading.set(true);
    const entryData: LedgerEntryCreate = this.entryForm.value;

    this.accountingService.createEntry(entryData).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.entryCreated.emit();
        this.close.emit();
      },
      error: (err) => {
        console.error(err);
        this.isLoading.set(false);
        alert("Error al guardar el asiento: " + (err.error?.detail || "Error desconocido"));
      }
    });
  }
}