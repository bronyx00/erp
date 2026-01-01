import { Component, EventEmitter, Output, inject, signal } from '@angular/core';
import { CommonModule, DatePipe, CurrencyPipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FinanceService, CashCloseResponse } from '../../../core/services/finance';

@Component({
  selector: 'app-cash-close-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe, CurrencyPipe, DecimalPipe],
  template: `
    <div class="fixed inset-0 z-[200] flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity" (click)="close()"></div>

        <div class="relative w-full max-w-4xl bg-slate-50 shadow-2xl rounded-2xl overflow-hidden flex flex-col max-h-[95vh] ring-1 ring-white/10">
            
            <div class="bg-white px-6 py-4 border-b border-slate-200 flex justify-between items-center">
                <div class="flex items-center gap-3">
                    <div class="h-10 w-10 bg-slate-900 rounded-xl flex items-center justify-center text-white shadow-lg shadow-slate-900/20">
                        <i class="fas" [class.fa-cash-register]="!result()" [class.fa-check-circle]="result()"></i>
                    </div>
                    <div>
                        <h2 class="text-lg font-bold text-slate-800">{{ result() ? 'Cierre Procesado' : 'Arqueo de Caja' }}</h2>
                        <p class="text-xs text-slate-500 font-medium">
                            {{ result() ? 'Resumen de operaciones y diferencias' : 'Ingrese los montos físicos contados' }}
                        </p>
                    </div>
                </div>
                <button (click)="close()" class="text-slate-400 hover:text-slate-700 transition">
                    <i class="fas fa-times text-lg"></i>
                </button>
            </div>

            <div *ngIf="!result()" class="flex-1 overflow-y-auto p-6">
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    
                    <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden group hover:border-emerald-300 transition-all">
                        <div class="bg-emerald-50/50 p-3 border-b border-emerald-100 flex items-center gap-2">
                            <i class="fas fa-dollar-sign text-emerald-600 bg-emerald-100 w-6 h-6 rounded-full flex items-center justify-center text-xs"></i>
                            <span class="text-xs font-bold text-emerald-800 uppercase tracking-wider">Moneda Dólar ($)</span>
                        </div>
                        <div class="p-5 space-y-5">
                            <div>
                                <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Efectivo Físico</label>
                                <input type="number" [(ngModel)]="declaredCashUsd" 
                                       class="w-full text-2xl font-black text-slate-700 bg-slate-50 border border-slate-200 rounded-lg p-3 text-right focus:ring-2 focus:ring-emerald-500 outline-none transition-all placeholder:text-slate-300" 
                                       placeholder="0.00">
                            </div>
                            <div>
                                <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Cierre de Lote (Puntos)</label>
                                <input type="number" [(ngModel)]="declaredCardUsd" 
                                       class="w-full text-lg font-bold text-slate-600 bg-slate-50 border border-slate-200 rounded-lg p-3 text-right focus:ring-2 focus:ring-emerald-500 outline-none transition-all placeholder:text-slate-300" 
                                       placeholder="0.00">
                            </div>
                        </div>
                    </div>

                    <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden group hover:border-indigo-300 transition-all">
                        <div class="bg-indigo-50/50 p-3 border-b border-indigo-100 flex items-center gap-2">
                            <span class="text-xs font-bold text-indigo-600 bg-indigo-100 w-6 h-6 rounded-full flex items-center justify-center">Bs</span>
                            <span class="text-xs font-bold text-indigo-800 uppercase tracking-wider">Moneda Bolívar (Bs.)</span>
                        </div>
                        <div class="p-5 space-y-5">
                            <div>
                                <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Efectivo Físico</label>
                                <input type="number" [(ngModel)]="declaredCashVes" 
                                       class="w-full text-2xl font-black text-slate-700 bg-slate-50 border border-slate-200 rounded-lg p-3 text-right focus:ring-2 focus:ring-indigo-500 outline-none transition-all placeholder:text-slate-300" 
                                       placeholder="0.00">
                            </div>
                            <div>
                                <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Cierre de Lote (Puntos)</label>
                                <input type="number" [(ngModel)]="declaredCardVes" 
                                       class="w-full text-lg font-bold text-slate-600 bg-slate-50 border border-slate-200 rounded-lg p-3 text-right focus:ring-2 focus:ring-indigo-500 outline-none transition-all placeholder:text-slate-300" 
                                       placeholder="0.00">
                            </div>
                        </div>
                    </div>

                </div>

                <div class="mt-6">
                    <label class="block text-xs font-bold text-slate-500 mb-2 pl-1">Notas del Cierre</label>
                    <textarea [(ngModel)]="notes" rows="2" placeholder="Observaciones sobre diferencias, billetes rotos, etc."
                              class="w-full p-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-slate-400 outline-none shadow-sm"></textarea>
                </div>
            </div>

            <div *ngIf="result()" class="flex-1 overflow-y-auto p-6 bg-slate-50">
                
                <div class="bg-white rounded-2xl border border-slate-200 p-6 mb-6 shadow-sm flex justify-between items-center relative overflow-hidden">
                    <div class="absolute left-0 top-0 bottom-0 w-1 bg-slate-800"></div>
                    <div>
                        <p class="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Total Ventas (Base)</p>
                        <h3 class="text-3xl font-black text-slate-800 tracking-tight">
                            {{ result()!.total_sales_usd | currency:'USD' }}
                        </h3>
                    </div>
                    <div class="text-right">
                        <p class="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Impuestos Recaudados</p>
                        <p class="text-xl font-bold text-slate-600">{{ result()!.total_tax_usd | currency:'USD' }}</p>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    
                    <div class="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col">
                        <div class="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                            <span class="text-sm font-bold text-slate-700 flex items-center gap-2">
                                <i class="fas fa-dollar-sign text-emerald-500"></i> Operaciones USD
                            </span>
                            <span class="text-[10px] bg-slate-200 text-slate-600 px-2 py-0.5 rounded font-bold">Efectivo + Tarjeta</span>
                        </div>
                        <div class="p-5 flex-1 space-y-4">
                            <div class="flex justify-between items-center">
                                <span class="text-xs font-bold text-slate-400 uppercase">Sistema</span>
                                <span class="text-sm font-medium text-slate-600">
                                    {{ (result()!.total_cash_usd + result()!.total_debit_card_usd) | currency:'USD' }}
                                </span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-xs font-bold text-slate-400 uppercase">Declarado</span>
                                <span class="text-lg font-bold text-slate-800">
                                    {{ (result()!.declared_cash_usd + result()!.declared_card_usd) | currency:'USD' }}
                                </span>
                            </div>
                            <div class="border-t border-dashed border-slate-200 pt-3 mt-2">
                                <div class="flex justify-between items-center bg-slate-50 p-2 rounded-lg">
                                    <span class="text-xs font-bold text-slate-500">Diferencia</span>
                                    <span class="font-black text-sm" [ngClass]="getDiffClass(result()!.difference_usd)">
                                        {{ result()!.difference_usd > 0 ? '+' : ''}}{{ result()!.difference_usd | currency:'USD' }}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col">
                        <div class="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                            <span class="text-sm font-bold text-slate-700 flex items-center gap-2">
                                <span class="text-indigo-500 font-black text-xs border border-indigo-500 rounded px-0.5">Bs</span> Operaciones VES
                            </span>
                            <span class="text-[10px] bg-slate-200 text-slate-600 px-2 py-0.5 rounded font-bold">Efectivo + Tarjeta</span>
                        </div>
                        <div class="p-5 flex-1 space-y-4">
                            <div class="flex justify-between items-center">
                                <span class="text-xs font-bold text-slate-400 uppercase">Sistema</span>
                                <span class="text-sm font-medium text-slate-600">
                                    Bs. {{ (result()!.total_cash_ves + result()!.total_debit_card_ves) | number:'1.2-2' }}
                                </span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-xs font-bold text-slate-400 uppercase">Declarado</span>
                                <span class="text-lg font-bold text-slate-800">
                                    Bs. {{ (result()!.declared_cash_ves + result()!.declared_card_ves) | number:'1.2-2' }}
                                </span>
                            </div>
                            <div class="border-t border-dashed border-slate-200 pt-3 mt-2">
                                <div class="flex justify-between items-center bg-slate-50 p-2 rounded-lg">
                                    <span class="text-xs font-bold text-slate-500">Diferencia</span>
                                    <span class="font-black text-sm" [ngClass]="getDiffClass(result()!.difference_ves)">
                                        {{ result()!.difference_ves > 0 ? '+' : ''}}Bs. {{ result()!.difference_ves | number:'1.2-2' }}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                </div>

                <div class="grid grid-cols-2 gap-4 mt-6">
                    <div class="bg-white p-3 rounded-lg border border-slate-100 text-center">
                        <p class="text-[10px] text-slate-400 uppercase font-bold">Crédito / Por Cobrar</p>
                        <p class="font-bold text-amber-600 text-sm mt-1">{{ result()!.total_credit_sales_usd | currency:'USD' }}</p>
                    </div>
                    <div class="bg-white p-3 rounded-lg border border-slate-100 text-center">
                        <p class="text-[10px] text-slate-400 uppercase font-bold">Transferencias (Zelle/PM)</p>
                        <p class="font-bold text-indigo-600 text-sm mt-1">{{ result()!.total_transfer_usd | currency:'USD' }}</p>
                    </div>
                </div>

            </div>

            <div class="p-4 bg-white border-t border-slate-200 flex justify-end gap-3 shrink-0 z-10">
                <button (click)="close()" class="px-5 py-2.5 text-slate-500 font-bold hover:bg-slate-50 rounded-xl transition text-sm">
                    {{ result() ? 'Cerrar' : 'Cancelar' }}
                </button>
                
                <button *ngIf="!result()" (click)="processClose()" [disabled]="isProcessing"
                        class="px-6 py-2.5 bg-slate-900 text-white font-bold rounded-xl hover:bg-slate-800 transition shadow-lg shadow-slate-900/20 flex items-center gap-2 active:scale-95 disabled:opacity-50">
                    <i *ngIf="isProcessing" class="fas fa-circle-notch fa-spin"></i>
                    <span>{{ isProcessing ? 'Procesando...' : 'Confirmar Cierre' }}</span>
                </button>

                <button *ngIf="result()" (click)="printReport()" 
                        class="px-6 py-2.5 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition shadow-lg shadow-indigo-500/30 flex items-center gap-2 active:scale-95">
                    <i class="fas fa-print"></i> Imprimir Reporte
                </button>
            </div>

        </div>
    </div>
  `
})
export class CashCloseModalComponent {
  @Output() onClose = new EventEmitter<boolean>();

  private financeService = inject(FinanceService);

  // Form Data
  declaredCashUsd: number = 0;
  declaredCashVes: number = 0;
  declaredCardUsd: number = 0;
  declaredCardVes: number = 0;
  notes: string = '';

  isProcessing = false;
  result = signal<CashCloseResponse | null>(null);

  processClose() {
    if (!confirm('¿Confirma el cierre de caja? Se procesarán todas las facturas pendientes.')) return;

    this.isProcessing = true;
    
    this.financeService.performCashClose({
        declared_cash_usd: this.declaredCashUsd,
        declared_cash_ves: this.declaredCashVes,
        declared_card_usd: this.declaredCardUsd, 
        declared_card_ves: this.declaredCardVes, 
        notes: this.notes
    }).subscribe({
        next: (res: any) => { // <--- Usamos 'any' temporalmente para parsear
            
            // CONVERSIÓN EXPLÍCITA DE STRING A NUMBER
            // Esto soluciona el problema de las sumas en el HTML
            const cleanResult: CashCloseResponse = {
                ...res,
                total_sales_usd: Number(res.total_sales_usd),
                total_tax_usd: Number(res.total_tax_usd),
                
                total_sales_ves: Number(res.total_sales_ves),
                total_tax_ves: Number(res.total_tax_ves),

                total_cash_usd: Number(res.total_cash_usd),
                total_debit_card_usd: Number(res.total_debit_card_usd),
                total_transfer_usd: Number(res.total_transfer_usd),
                total_credit_sales_usd: Number(res.total_credit_sales_usd),

                total_cash_ves: Number(res.total_cash_ves),
                total_debit_card_ves: Number(res.total_debit_card_ves),
                total_transfer_ves: Number(res.total_transfer_ves),
                total_credit_sales_ves: Number(res.total_credit_sales_ves),

                declared_cash_usd: Number(res.declared_cash_usd),
                declared_cash_ves: Number(res.declared_cash_ves),
                declared_card_usd: Number(res.declared_card_usd),
                declared_card_ves: Number(res.declared_card_ves),

                difference_usd: Number(res.difference_usd),
                difference_ves: Number(res.difference_ves)
            };

            this.result.set(cleanResult);
            this.isProcessing = false;
        },
        error: (err) => {
            console.error(err);
            alert('Error: ' + (err.error?.detail || err.message));
            this.isProcessing = false;
        }
    });
  }
  
  printReport() {
      window.print();
  }

  close(success: boolean = false) {
      this.onClose.emit(this.result() !== null || success);
  }

  getDiffClass(val: number): string {
      // Pequeño margen de tolerancia visual
      if (Math.abs(val) < 0.01) return 'text-slate-400 bg-slate-100'; 
      return val >= 0 ? 'text-emerald-700 bg-emerald-100' : 'text-rose-700 bg-rose-100';
  }
}