import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule, CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { AccountingService } from '../services/accounting.service';
import { Account } from '../models/accounting.models';
import { EntryModalComponent } from '../components/entry-modal/entry-modal.component';
import { AccountFormModalComponent } from '../components/account-form-modal/account-form-modal.component';

@Component({
  selector: 'app-chart-of-accounts',
  standalone: true,
  imports: [CommonModule, CurrencyPipe, EntryModalComponent, FormsModule, AccountFormModalComponent],
  template: `
    <div class="space-y-6 animate-in fade-in duration-500">
      
      <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 class="text-2xl font-bold text-slate-800">Plan de Cuentas</h2>
          <p class="text-slate-500 text-sm">Gestiona la estructura financiera y registra operaciones.</p>
        </div>
        
        <div class="flex gap-3">
        <button (click)="openAccountModal(null, null)" 
                class="px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 font-medium transition shadow-sm text-sm flex items-center gap-2">
          <i class="fas fa-folder-plus"></i> Crear Cuenta
        </button>
          <button (click)="refreshData()" class="p-2 text-slate-400 hover:text-indigo-600 transition" title="Recargar datos">
            <i class="fas fa-sync-alt" [class.fa-spin]="isLoading()"></i>
          </button>

          <button (click)="openEntryModal()" 
                  class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium transition shadow-md shadow-indigo-200 text-sm flex items-center gap-2">
            <i class="fas fa-plus"></i> Nueva Operación
          </button>
        </div>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden relative min-h-[300px]">
        
        <div *ngIf="isLoading()" class="absolute inset-0 bg-white/80 backdrop-blur-sm z-10 flex flex-col items-center justify-center text-indigo-600">
          <i class="fas fa-circle-notch fa-spin text-3xl mb-3"></i>
          <p class="text-sm font-semibold">Sincronizando cuentas...</p>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-sm text-left">
            <thead class="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th class="px-6 py-3 w-32">Código</th>
                <th class="px-6 py-3">Nombre de la Cuenta</th>
                <th class="px-6 py-3 w-32 text-center">Tipo</th>
                <th class="px-6 py-3 w-16"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              
              @for (acc of sortedAccounts(); track acc.id) {
                <tr class="hover:bg-slate-50 transition-colors group">
                  <td class="px-6 py-3 font-mono text-slate-600">{{ acc.code }}</td>
                  <td class="px-6 py-3">
                    <div [style.padding-left.px]="(acc.level - 1) * 24" class="flex items-center gap-2">
                      <i [class]="acc.is_transactional ? 'fas fa-circle text-[6px] text-slate-300' : 'fas fa-folder text-slate-400'"></i>
                      <span [class.font-bold]="!acc.is_transactional" 
                            [class.text-slate-800]="!acc.is_transactional"
                            [class.text-slate-600]="acc.is_transactional">
                        {{ acc.name }}
                      </span>
                    </div>
                  </td>
                  <td class="px-6 py-3 text-center">
                    <span [class]="getTypeBadgeClass(acc.account_type)" 
                          class="px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide">
                      {{ getShortType(acc.account_type) }}
                    </span>
                  </td>
                  <td class="px-6 py-3 text-right opacity-0 group-hover:opacity-100 transition-opacity">
                    <button *ngIf="!acc.is_transactional" 
                            (click)="openAccountModal(null, acc)"
                            class="text-slate-400 hover:text-indigo-600" 
                            title="Agregar sub-cuenta">
                        <i class="fas fa-folder-plus"></i>
                    </button>

                    <button *ngIf="acc.level > 2"
                            (click)="openAccountModal(acc, null)" 
                            class="text-slate-400 hover:text-blue-600"
                            title="Editar nombre">
                        <i class="fas fa-pencil-alt"></i>
                    </button>
                  </td>
                </tr>
              } @empty {
                
                <tr>
                  <td colspan="5" class="px-6 py-16 text-center text-slate-500">
                    <div class="flex flex-col items-center max-w-lg mx-auto bg-slate-50 p-8 rounded-2xl border border-slate-100">
                      
                      <div class="h-16 w-16 bg-white border border-slate-200 rounded-full flex items-center justify-center mb-4 text-indigo-600 text-2xl shadow-sm">
                        <i class="fas fa-boxes"></i>
                      </div>
                      
                      <h3 class="text-xl font-bold text-slate-800 mb-2">Configura tu Catálogo de Cuentas</h3>
                      <p class="text-sm text-slate-500 mb-6 text-center">
                        Para comenzar, necesitamos cargar las cuentas contables estándar (VEN-NIF). 
                        Selecciona el rubro de tu empresa para optimizar las cuentas.
                      </p>
                      
                      <div class="w-full mb-4 text-left">
                        <label class="block text-xs font-bold text-slate-500 uppercase mb-1 ml-1">Rubro / Sector</label>
                        <select [(ngModel)]="selectedSector" 
                                class="w-full rounded-lg border-slate-300 text-sm focus:ring-indigo-500 focus:border-indigo-500 py-2.5 shadow-sm">
                          <option value="commerce">Comercio / Retail (Estándar)</option>
                          <option value="services">Servicios / Profesionales</option>
                          <option value="industry">Manufactura / Industria</option>
                          <option value="agriculture">Agropecuario / Ganadería</option>
                        </select>
                      </div>

                      <div class="flex gap-3 w-full">
                        <button class="flex-1 px-4 py-2.5 bg-white border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 font-medium transition text-sm">
                          <i class="fas fa-file-excel mr-2"></i> Importar Excel
                        </button>

                        <button (click)="loadDefaultPuc()" 
                                [disabled]="isLoading()"
                                class="flex-1 px-4 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-bold transition shadow-lg shadow-indigo-200 text-sm flex items-center justify-center gap-2">
                          <span *ngIf="!isLoading()"><i class="fas fa-magic"></i> Instalar Cuentas</span>
                          <span *ngIf="isLoading()"><i class="fas fa-circle-notch fa-spin"></i> Instalando...</span>
                        </button>
                      </div>

                    </div>
                  </td>
                </tr>

              }
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <app-entry-modal 
      *ngIf="showModal()" 
      (close)="closeEntryModal()"
      (entryCreated)="refreshData()">
    </app-entry-modal>

    <app-account-form-modal 
        *ngIf="showAccountModal()"
        [accountToEdit]="selectedAccountToEdit()"
        [parentAccount]="selectedParentAccount()"
        (close)="closeAccountModal()"
        (saved)="refreshData()">
    </app-account-form-modal>
  `
})
export class ChartOfAccountsComponent implements OnInit {
    private accountingService = inject(AccountingService);
    
    // Signals
    accounts = signal<Account[]>([]);
    showModal = signal(false);
    showAccountModal = signal(false);
    selectedAccountToEdit = signal<Account | null>(null);
    selectedParentAccount = signal<Account | null>(null);
    isLoading = signal(false);

    selectedSector: string = 'commerce';

    sortedAccounts = computed(() => {
      return [...this.accounts()].sort((a, b) => {
        return a.code.localeCompare(b.code, undefined, { numeric: true, sensitivity: 'base' });
      });
    });

    ngOnInit() {
        this.refreshData();
    }

    refreshData() {
        this.isLoading.set(true);
        this.accountingService.getAccounts().subscribe({
            next: (data) => {
                this.accounts.set(data);
                this.isLoading.set(false);
            },
            error: (err) => {
                console.error('Error cargando cuentas:', err);
                this.isLoading.set(false);
            }
        });
    }

    // --- UI HELPERS ---
    loadDefaultPuc() {
        const sectorName = this.getSectorName(this.selectedSector);
        
        if (!confirm(`¿Confirmas cargar el catálogo estándar para "${sectorName}"? \nSe agregarán cuentas base y específicas del sector.`)) {
        return;
        }

        this.isLoading.set(true);
        
        // Enviamos el sector seleccionado al servicio
        this.accountingService.seedDefaultPuc(this.selectedSector).subscribe({
        next: (res) => {
            this.refreshData(); // Recarga la tabla
            // Opcional: Mostrar mensaje de éxito
            console.log(res.message);
        },
        error: (err) => {
            console.error('Error seeding PUC:', err);
            this.isLoading.set(false);
            alert('Hubo un error cargando el catálogo. Revisa la consola o intenta de nuevo.');
        }
        });
    }

    getSectorName(key: string): string {
        const map: any = {
        'commerce': 'Comercio y Retail',
        'services': 'Servicios Profesionales',
        'industry': 'Industria y Manufactura',
        'agriculture': 'Agropecuario'
        };
        return map[key] || 'General';
    }
  
  openAccountModal(edit: Account | null, parent: Account | null) {
    this.selectedAccountToEdit.set(edit);
    this.selectedParentAccount.set(parent);
    this.showAccountModal.set(true);
  }

  closeAccountModal() {
    this.showAccountModal.set(false);
  }

    openEntryModal() { this.showModal.set(true); }
    closeEntryModal() { this.showModal.set(false); }

    getShortType(type: string): string {
        const map: Record<string, string> = {
        'ASSET': 'ACT', 'LIABILITY': 'PAS', 'EQUITY': 'PAT', 
        'REVENUE': 'ING', 'EXPENSE': 'GAS'
        };
        return map[type] || type;
    }

    getTypeBadgeClass(type: string): string {
        const map: Record<string, string> = {
        'ASSET': 'bg-emerald-100 text-emerald-700',
        'LIABILITY': 'bg-amber-100 text-amber-700',
        'EQUITY': 'bg-indigo-100 text-indigo-700',
        'REVENUE': 'bg-blue-100 text-blue-700',
        'EXPENSE': 'bg-rose-100 text-rose-700'
        };
        return map[type] || 'bg-slate-100 text-slate-600';
    }
}