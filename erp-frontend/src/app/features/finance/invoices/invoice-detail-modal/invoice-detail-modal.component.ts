import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Invoice } from '../../../../core/services/finance';

@Component({
  selector: 'app-invoice-detail-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="fixed inset-0 z-[100] flex items-center justify-center p-4 animate-in fade-in duration-200">
        
        <div class="absolute inset-0 bg-black/20 backdrop-blur-sm transition-opacity" 
             (click)="onClose.emit()">
        </div>

        <div class="relative bg-white w-full max-w-2xl shadow-2xl rounded-lg overflow-hidden flex flex-col max-h-[90vh] transform transition-all scale-100">
            
            <div class="bg-slate-50/80 border-b border-slate-100 p-8 flex justify-between items-start">
                <div>
                    <div class="flex items-center gap-3 mb-3">
                        <div class="h-10 w-10 bg-indigo-600 rounded-lg flex items-center justify-center text-white shadow-lg shadow-indigo-500/30">
                            <i class="fas fa-cube text-xl"></i>
                        </div>
                        <div>
                            <h1 class="font-bold text-slate-800 text-lg leading-tight">{{ invoice.company_name || 'Mi Empresa C.A.' }}</h1>
                            <p class="text-xs text-slate-500 font-mono">{{ invoice.company_rif || 'RIF: N/A' }}</p>
                        </div>
                    </div>
                    <p class="text-xs text-slate-500 max-w-[250px] leading-relaxed pl-1">
                        {{ invoice.company_address || 'Dirección no registrada' }}
                    </p>
                </div>

                <div class="text-right">
                    <h2 class="text-2xl font-black text-slate-800 tracking-tight">FACTURA</h2>
                    <p class="font-mono text-indigo-600 font-bold text-lg mt-1">#{{ invoice.control_number || invoice.invoice_number }}</p>
                    
                    <div class="mt-4 space-y-0.5">
                        <p class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Fecha de Emisión</p>
                        <p class="text-sm font-bold text-slate-700">{{ invoice.created_at | date:'dd/MM/yyyy h:mm a' }}</p>
                    </div>
                </div>
            </div>

            <div class="p-8 pb-4 border-b border-slate-100">
                <div class="flex justify-between items-start bg-slate-50/50 rounded-xl p-4 border border-slate-100">
                    <div>
                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Cliente</p>
                        <h3 class="font-bold text-slate-800 text-base">{{ invoice.customer_name || 'Cliente Genérico' }}</h3>
                        <p class="text-xs text-slate-500 font-mono mt-0.5">{{ invoice.customer_rif || 'V-00000000' }}</p>
                        <p *ngIf="invoice.customer_address" class="text-xs text-slate-400 mt-1 max-w-xs">{{ invoice.customer_address }}</p>
                    </div>
                    <div class="text-right">
                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Estado</p>
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border"
                              [ngClass]="getStatusClass(invoice.status)">
                            {{ getStatusLabel(invoice.status) }}
                        </span>
                    </div>
                </div>
            </div>

            <div class="flex-1 overflow-y-auto p-8 pt-2">
                <table class="w-full text-sm text-left">
                    <thead class="text-xs text-slate-400 uppercase font-bold border-b border-slate-100">
                        <tr>
                            <th class="py-3 pl-2 font-semibold">Descripción</th>
                            <th class="py-3 text-right font-semibold">Cant.</th>
                            <th class="py-3 text-right font-semibold">Precio</th>
                            <th class="py-3 text-right pr-2 font-semibold">Total</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-50">
                        @for (item of invoice.items; track $index) {
                            <tr>
                                <td class="py-3 pl-2 font-medium text-slate-600">{{ item.product_name }}</td>
                                <td class="py-3 text-right text-slate-500">{{ item.quantity }}</td>
                                <td class="py-3 text-right text-slate-500">{{ item.unit_price | currency: invoice.currency }}</td>
                                <td class="py-3 text-right font-bold text-slate-700 pr-2">{{ item.total_price | currency: invoice.currency }}</td>
                            </tr>
                        }
                    </tbody>
                </table>
            </div>

            <div class="bg-slate-50/80 p-8 pt-6 border-t border-slate-100">
                <div class="flex justify-end">
                    <div class="w-72 space-y-3">
                        <div class="flex justify-between text-sm text-slate-500">
                            <span>Subtotal</span>
                            <span class="font-medium">{{ invoice.subtotal_usd | currency: invoice.currency }}</span>
                        </div>
                        <div class="flex justify-between text-sm text-slate-500">
                            <span>Impuestos (16%)</span>
                            <span class="font-medium">{{ invoice.tax_amount_usd | currency: invoice.currency }}</span>
                        </div>
                        <div class="flex justify-between items-center pt-3 border-t border-slate-200">
                            <span class="font-bold text-slate-800 text-lg">Total General</span>
                            <span class="text-2xl font-black text-indigo-600 tracking-tight">{{ invoice.total_usd | currency: invoice.currency }}</span>
                        </div>
                        
                        <div class="bg-white border border-slate-200 rounded-lg p-3 text-right shadow-sm mt-2">
                            <p class="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Pagadero en Bolívares</p>
                            <p class="text-base font-bold text-slate-700">
                                Bs. {{ (invoice.amount_ves || (invoice.total_usd * (invoice.exchange_rate || 0))) | number:'1.2-2' }}
                            </p>
                            <p class="text-[10px] text-slate-400 mt-1">Tasa: {{ invoice.exchange_rate | number:'1.2-4' }}</p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="p-4 border-t border-slate-100 flex justify-end bg-white">
                <button (click)="onClose.emit()" class="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold transition shadow-lg shadow-slate-900/10 text-sm active:scale-95">
                    Cerrar Detalle
                </button>
            </div>

        </div>
    </div>
  `
})
export class InvoiceDetailModalComponent {
  @Input() invoice!: Invoice;
  @Output() onClose = new EventEmitter<void>();

  getStatusClass(status: string) {
      switch(status) {
          case 'PAID': return 'bg-emerald-50 text-emerald-700 border-emerald-100';
          case 'PARTIALLY_PAID': return 'bg-amber-50 text-amber-700 border-amber-100';
          case 'VOID': return 'bg-rose-50 text-rose-700 border-rose-100';
          default: return 'bg-slate-50 text-slate-600 border-slate-100';
      }
  }

  getStatusLabel(status: string) {
      const map: any = { 'PAID': 'PAGADA', 'PARTIALLY_PAID': 'ABONADA', 'VOID': 'ANULADA', 'ISSUED': 'EMITIDA' };
      return map[status] || status;
  }
}