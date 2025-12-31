import { Component, EventEmitter, Input, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Quote } from '../../../../core/services/finance';

@Component({
  selector: 'app-quote-detail-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="fixed inset-0 z-[100] flex items-center justify-center p-4 animate-in fade-in duration-200">
        
        <div class="absolute inset-0 bg-[#0000004d] backdrop-blur-sm transition-opacity" 
             (click)="onClose.emit()">
        </div>

        <div class="relative bg-white w-full max-w-3xl shadow-2xl rounded-lg overflow-hidden flex flex-col max-h-[90vh] transform transition-all scale-100 ring-1 ring-slate-900/5">
            
            <div class="bg-slate-50/80 border-b border-slate-100 p-8 flex justify-between items-start">
                <div>
                    <div class="flex items-center gap-3 mb-3">
                        <div class="h-10 w-10 bg-indigo-600 rounded-lg flex items-center justify-center text-white shadow-lg shadow-indigo-500/30">
                            <i class="fas fa-file-contract text-xl"></i>
                        </div>
                        <div>
                            <h1 class="font-bold text-slate-800 text-lg leading-tight">{{ quote.company_name }}</h1>
                            <p class="text-xs text-slate-500 font-mono">{{ quote.company_rif }}</p>
                        </div>
                    </div>
                    <p class="text-xs text-slate-500 max-w-[250px] leading-relaxed pl-1">
                        {{ quote.company_address }}
                    </p>
                </div>

                <div class="text-right">
                    <h2 class="text-2xl font-black text-slate-800 tracking-tight">COTIZACIÓN</h2>
                    <p class="font-mono text-indigo-600 font-bold text-lg mt-1">{{ quote.quote_number }}</p>
                    
                    <div class="mt-4 space-y-0.5">
                        <p class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Fecha de Emisión</p>
                        <p class="text-sm font-bold text-slate-700">{{ quote.date_issued | date:'dd/MM/yyyy' }}</p>
                    </div>
                    <div class="mt-2 space-y-0.5">
                        <p class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Válida Hasta</p>
                        <p class="text-sm font-bold text-rose-600">{{ quote.date_expires | date:'dd/MM/yyyy' }}</p>
                    </div>
                </div>
            </div>

            <div class="p-8 pb-4 border-b border-slate-100">
                <div class="flex justify-between items-start bg-slate-50/50 rounded-xl p-4 border border-slate-100">
                    <div class="flex-1">
                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Preparado para:</p>
                        
                        <h3 class="font-bold text-slate-800 text-base">{{ quote.customer_name }}</h3>
                        
                        <div class="grid grid-cols-2 gap-x-8 gap-y-1 mt-2">
                            <div>
                                <p class="text-xs text-slate-400 uppercase font-bold text-[9px]">Documento / RIF</p>
                                <p class="text-xs text-slate-600 font-mono">{{ quote.customer_rif }}</p>
                            </div>
                            <div *ngIf="quote.customer_phone">
                                <p class="text-xs text-slate-400 uppercase font-bold text-[9px]">Teléfono</p>
                                <p class="text-xs text-slate-600">{{ quote.customer_phone }}</p>
                            </div>
                            <div *ngIf="quote.customer_email" class="col-span-2 mt-1">
                                <p class="text-xs text-slate-400 uppercase font-bold text-[9px]">Email</p>
                                <p class="text-xs text-slate-600">{{ quote.customer_email }}</p>
                            </div>
                            <div *ngIf="quote.customer_address" class="col-span-2 mt-1">
                                <p class="text-xs text-slate-400 uppercase font-bold text-[9px]">Dirección</p>
                                <p class="text-xs text-slate-600 max-w-sm">{{ quote.customer_address }}</p>
                            </div>
                        </div>
                    </div>

                    <div class="text-right pl-4 border-l border-slate-200 ml-4">
                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Estado</p>
                        <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border shadow-sm"
                              [ngClass]="getStatusClass(quote.status)">
                            {{ getStatusLabel(quote.status) }}
                        </span>
                        
                        <div class="mt-4 text-right">
                            <p class="text-[10px] text-slate-400 uppercase font-bold">Moneda Base</p>
                            <p class="font-bold text-indigo-600">{{ quote.currency }}</p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="flex-1 overflow-y-auto p-8 pt-2">
                <table class="w-full text-sm text-left">
                    <thead class="text-xs text-slate-400 uppercase font-bold border-b border-slate-100">
                        <tr>
                            <th class="py-3 pl-2 font-semibold">Descripción</th>
                            <th class="py-3 text-right font-semibold">Cant.</th>
                            <th class="py-3 text-right font-semibold">Precio Unit.</th>
                            <th class="py-3 text-right pr-2 font-semibold">Total</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-50">
                        @for (item of quote.items; track $index) {
                            <tr class="hover:bg-slate-50/50 transition">
                                <td class="py-3 pl-2">
                                    <p class="font-medium text-slate-700">{{ item.product_name }}</p>
                                    <p *ngIf="item.description" class="text-[11px] text-slate-400 mt-0.5 italic">{{ item.description }}</p>
                                </td>
                                <td class="py-3 text-right text-slate-500 font-mono">{{ item.quantity }}</td>
                                <td class="py-3 text-right text-slate-600 font-mono">{{ item.unit_price | currency: quote.currency }}</td>
                                <td class="py-3 text-right font-bold text-slate-800 font-mono pr-2">{{ item.total_price | currency: quote.currency }}</td>
                            </tr>
                        }
                    </tbody>
                </table>
            </div>

            <div class="bg-slate-50/80 p-8 pt-6 border-t border-slate-100">
                <div class="flex flex-col md:flex-row gap-8">
                    
                    <div class="flex-1 space-y-4">
                        <div *ngIf="quote.notes" class="bg-white p-3 rounded-lg border border-slate-200/60 shadow-sm">
                            <p class="text-[10px] font-bold text-slate-400 uppercase mb-1">Observaciones</p>
                            <p class="text-xs text-slate-600 leading-relaxed">{{ quote.notes }}</p>
                        </div>
                        <div *ngIf="quote.terms" class="bg-white p-3 rounded-lg border border-slate-200/60 shadow-sm">
                            <p class="text-[10px] font-bold text-slate-400 uppercase mb-1">Términos y Condiciones</p>
                            <p class="text-xs text-slate-600 leading-relaxed">{{ quote.terms }}</p>
                        </div>
                    </div>

                    <div class="w-72 space-y-3">
                        <div class="flex justify-between text-sm text-slate-500">
                            <span>Subtotal</span>
                            <span class="font-medium">{{ quote.subtotal | currency: quote.currency }}</span>
                        </div>
                        <div class="flex justify-between text-sm text-slate-500">
                            <span>Impuestos (16%)</span>
                            <span class="font-medium">{{ quote.tax_amount | currency: quote.currency }}</span>
                        </div>
                        <div class="flex justify-between items-center pt-3 border-t border-slate-200">
                            <span class="font-bold text-slate-800 text-lg">Total</span>
                            <span class="text-3xl font-black text-indigo-600 tracking-tight">{{ quote.total | currency: quote.currency }}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="p-4 border-t border-slate-100 flex justify-between items-center bg-white">
                <button class="text-slate-400 hover:text-slate-600 text-sm font-bold flex items-center gap-2 px-3 py-2 rounded hover:bg-slate-50 transition">
                    <i class="fas fa-print"></i> Imprimir PDF
                </button>

                <div class="flex gap-3">
                    <button (click)="onClose.emit()" class="px-5 py-2 text-slate-600 font-bold hover:bg-slate-100 rounded-lg transition text-sm">
                        Cerrar
                    </button>
                    
                    <button *ngIf="quote.status === 'SENT' || quote.status === 'DRAFT'" 
                            (click)="onConvert.emit(quote)"
                            class="px-6 py-2.5 bg-slate-900 hover:bg-black text-white rounded-xl font-bold transition shadow-lg shadow-slate-900/20 text-sm flex items-center gap-2 transform active:scale-95">
                        <i class="fas fa-check-circle text-indigo-400"></i> Aprobar y Facturar
                    </button>
                </div>
            </div>

        </div>
    </div>
  `
})
export class QuoteDetailModalComponent {
  @Input() quote!: Quote;
  @Output() onClose = new EventEmitter<void>();
  @Output() onConvert = new EventEmitter<Quote>();

  // Señales para datos de la empresa
  tenantName = signal('Cargando empresa...');
  tenantRif = signal('');
  tenantAddress = signal('');

  getStatusClass(status: string) {
      switch(status) {
          case 'SENT': return 'bg-blue-50 text-blue-700 border-blue-200';
          case 'INVOICED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
          case 'REJECTED': return 'bg-rose-50 text-rose-700 border-rose-200';
          case 'DRAFT': return 'bg-slate-100 text-slate-600 border-slate-200';
          default: return 'bg-slate-50 text-slate-600 border-slate-200';
      }
  }

  getStatusLabel(status: string) {
      const map: any = { 'SENT': 'ENVIADA', 'INVOICED': 'FACTURADA', 'DRAFT': 'BORRADOR', 'REJECTED': 'RECHAZADA' };
      return map[status] || status;
  }
}