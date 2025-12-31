import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Invoice } from '../../../../core/services/finance';

@Component({
  selector: 'app-invoice-detail-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="fixed inset-0 z-[100] flex items-center justify-center p-4 animate-in fade-in duration-200">
        
        <div class="absolute inset-0 bg-[#0000004d] backdrop-blur-sm transition-opacity" (click)="onClose.emit()"></div>

        <div class="relative bg-white w-full max-w-2xl shadow-2xl rounded-lg overflow-hidden flex flex-col max-h-[90vh] ring-1 ring-white/20 transform transition-all scale-100">
            
            <div class="bg-slate-50/90 border-b border-slate-100 p-8 flex justify-between items-start">
                <div>
                    <div class="flex items-center gap-3 mb-3">
                        <div class="h-10 w-10 bg-indigo-600 rounded-lg flex items-center justify-center text-white shadow-lg shadow-indigo-500/30">
                            <i class="fas fa-cube text-xl"></i>
                        </div>
                        <div>
                            <h1 class="font-bold text-slate-800 text-lg leading-tight">{{ invoice.company_name || 'Mi Empresa' }}</h1>
                            <p class="text-xs text-slate-500 font-mono">{{ invoice.company_rif }}</p>
                        </div>
                    </div>
                    <p class="text-xs text-slate-500 max-w-[250px] leading-relaxed pl-1">
                        {{ invoice.company_address || 'Dirección no registrada' }}
                    </p>
                </div>

                <div class="text-right">
                    <h2 class="text-2xl font-black text-slate-800 tracking-tight">FACTURA</h2>
                    <p class="font-mono text-indigo-600 font-bold text-lg mt-1">#{{ invoice.control_number || invoice.invoice_number }}</p>
                    <p class="text-xs font-bold text-slate-400 mt-2">{{ invoice.created_at | date:'dd/MM/yyyy' }}</p>
                </div>
            </div>

            <div class="p-8 pb-4 border-b border-slate-100">
                <div class="flex justify-between items-start bg-slate-50/50 rounded-xl p-4 border border-slate-100">
                    <div>
                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Cliente</p>
                        <h3 class="font-bold text-slate-800 text-base">{{ invoice.customer_name || 'Cliente Genérico' }}</h3>
                        <p class="text-xs text-slate-500 font-mono mt-0.5">{{ invoice.customer_rif }}</p>
                    </div>
                    <div class="text-right">
                        <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border"
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
                            <th class="py-3 pl-2">Descripción</th>
                            <th class="py-3 text-right">Cant.</th>
                            <th class="py-3 text-right">Precio</th>
                            <th class="py-3 text-right pr-2">Total</th>
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

            <div class="bg-slate-50 p-8 pt-6 border-t border-slate-100">
                <div class="flex flex-col md:flex-row gap-8 items-start">
                    
                    <div class="flex-1">
                        @if (invoice.payments && invoice.payments.length > 0) {
                            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Abonos Realizados</p>
                            <div class="space-y-1">
                                @for (pay of invoice.payments; track pay.id) {
                                    <div class="flex justify-between text-xs text-slate-500 border-b border-slate-100 pb-1">
                                        <span>{{ pay.created_at | date:'dd/MM' }} - {{ getMethodLabel(pay.payment_method) }}</span>
                                        <span class="font-mono text-emerald-600 font-medium">
                                            {{ pay.amount | number:'1.2-2' }} 
                                            <span class="text-[10px] font-bold text-slate-400 ml-1">
                                                {{ pay.currency === 'VES' ? 'Bs.' : pay.currency }}
                                            </span>
                                        </span>
                                    </div>
                                }
                            </div>
                        }
                    </div>

                    <div class="w-64 space-y-2">
                        
                        <div class="flex justify-between text-sm text-slate-500">
                            <span>Subtotal</span>
                            <span class="font-medium">{{ invoice.subtotal_usd | currency: invoice.currency }}</span>
                        </div>
                        <div class="flex justify-between text-sm text-slate-500 pb-2 border-b border-slate-200">
                            <span>Impuestos (16%)</span>
                            <span class="font-medium">{{ invoice.tax_amount_usd | currency: invoice.currency }}</span>
                        </div>
                        <div class="flex justify-between items-center text-lg font-bold text-slate-800 pt-1">
                            <span>Total</span>
                            <span>{{ invoice.total_usd | currency: invoice.currency }}</span>
                        </div>

                        @if (invoice.status !== 'PAID' && invoice.balance_due > 0.01) {
                            <div class="bg-white rounded border border-rose-100 p-3 mt-3 shadow-sm">
                                <div class="flex justify-between text-xs text-slate-400 mb-1">
                                    <span>Abonado Total</span>
                                    <span class="text-emerald-600 font-bold">- {{ invoice.total_paid | currency:'USD' }}</span>
                                </div>
                                <div class="flex justify-between items-center border-t border-dashed border-rose-100 pt-2 mt-1">
                                    <span class="text-xs font-bold text-rose-500 uppercase tracking-wider">Pendiente</span>
                                    <span class="text-xl font-black text-rose-600">{{ invoice.balance_due | currency:'USD' }}</span>
                                </div>
                                
                                <button (click)="onPay.emit(invoice)" 
                                        class="w-full mt-3 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold py-2 rounded transition shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-1">
                                    <i class="fas fa-hand-holding-usd"></i> Registrar Pago
                                </button>
                            </div>
                        }
                    </div>
                </div>
            </div>

            <div class="p-4 border-t border-slate-100 flex justify-end bg-white">
                <button (click)="onClose.emit()" class="text-slate-500 font-bold hover:text-slate-800 text-sm px-4">
                    Cerrar
                </button>
            </div>

        </div>
    </div>
  `
})
export class InvoiceDetailModalComponent {
    @Input() invoice!: Invoice;
    @Output() onClose = new EventEmitter<void>();
    @Output() onPay = new EventEmitter<Invoice>();

    getStatusClass(status: string) {
        switch(status) {
            case 'PAID': return 'bg-emerald-50 text-emerald-700 border-emerald-100';
            case 'PARTIALLY_PAID': return 'bg-amber-50 text-amber-700 border-amber-100';
            case 'VOID': return 'bg-rose-50 text-rose-700 border-rose-100 line-through opacity-70';
            default: return 'bg-slate-50 text-slate-600 border-slate-100';
        }
    }

    getStatusLabel(status: string) {
        const map: any = { 'PAID': 'PAGADA', 'PARTIALLY_PAID': 'ABONADA', 'VOID': 'ANULADA', 'ISSUED': 'POR PAGAR' };
        return map[status] || status;
    }

    getMethodLabel(method: string) {
        const map: any = { 'CASH': 'Efectivo', 'ZELLE': 'Zelle', 'PAGO_MOVIL': 'Pago Móvil', 'DEBIT_CARD': 'T. Débito', 'TRANSFER': 'Transf.' };
        return map[method] || method;
    }
}