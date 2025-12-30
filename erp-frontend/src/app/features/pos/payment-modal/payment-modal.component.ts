import { Component, EventEmitter, Input, Output, signal, computed, ViewChildren, ViewChild, ElementRef, QueryList, HostListener, AfterViewInit, inject, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
    selector: 'app-payment-modal',
    standalone: true,
    imports: [CommonModule, FormsModule],
    template: `
    <div class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200" (click)="onCancel.emit()">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden" (click)="$event.stopPropagation()">

            <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                <div>
                    <h3 class="font-bold text-slate-800">Procesar Pago</h3>
                    <p class="text-xs text-slate-500">Navegue con flechas. Enter para seleccionar.</p>
                    <p class="text-xs text-slate-500">F2 para cambiar de moneda.</p>
                </div>
                <div class="flex bg-white border border-slate-200 rounded-lg p-1">
                    <button (click)="setCurrency('VES')"
                            [class.bg-slate-100]="currency() === 'VES'"
                            [class.text-slate-800]="currency() === 'VES'"
                            [class.font-bold]="currency() === 'VES'"
                            class="px-3 py-1 text-xs rounded-md text-slate-500 transition-all focus:outline-none focus:ring-2 focus:ring-slate-400">
                        Bs.
                    </button>
                    <button (click)="setCurrency('USD')"
                            [class.bg-indigo-50]="currency() === 'USD'"
                            [class.text-indigo-600]="currency() === 'USD'"
                            [class.font-bold]="currency() === 'USD'"
                            class="px-3 py-1 text-xs rounded-md text-slate-500 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-400">
                        USD
                    </button>
                </div>
            </div>

            <div class="p-6">

                <div class="text-center mb-6">
                    <p class="text-xs text-slate-400 uppercase tracking-wider font-bold mb-1">Monto a Pagar</p>
                    <div class="flex justify-center items-center gap-2">
                        <span class="text-xl text-slate-400 font-bold">
                        {{ currency() === 'VES' ? 'Bs.' : '$' }}
                        </span>

                        <input #amountInput
                                type="number" 
                                [(ngModel)]="paymentAmount"
                                (keydown.enter)="confirmPayment($event)"
                                class="text-4xl font-extrabold text-slate-800 tracking-tight text-center w-48 border-b-2 border-slate-200 focus:border-indigo-600 outline-none bg-transparent transition-colors p-1"
                                placeholder="0.00">
                    </div>

                    @if (currency() === 'VES') {
                        <p class="text-xs text-slate-400 mt-2 font-mono">Ref: $ {{ amountUsd | number:'1.2-2' }} @ {{ exchangeRate | number:'1.2-2' }}</p>
                    }
                </div>

                <div class="grid grid-cols-3 gap-3 mb-6">
                    @for (method of currentMethods(); track method.id; let i = $index) {
                        <button #methodBtn
                                (click)="selectMethod(method.id)"
                                (keydown.enter)="onEnterOnMethod(method.id, $event)"
                                [class.ring-2]="selectedMethod() === method.id"
                                [class.ring-indigo-500]="selectedMethod() === method.id"
                                [class.bg-indigo-50]="selectedMethod() === method.id"
                                [class.text-indigo-700]="selectedMethod() === method.id"
                                [class.border-indigo-200]="selectedMethod() === method.id"
                                [class.ring-2-slate]="focusedIndex === i"
                                class="flex flex-col items-center justify-center p-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300 transition-all group h-24 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-slate-50 relative">

                            <div *ngIf="focusedIndex === i" class="absolute inset-0 border-2 border-indigo-300 rounded-xl pointer-events-none animate-pulse"></div>

                            <i [class]="method.icon" class="text-2xl mb-2 text-slate-400 group-hover:text-indigo-500 transition-colors"
                            [class.text-indigo-600]="selectedMethod() === method.id"></i>
                            <span class="text-[10px] font-bold uppercase text-center leading-tight">{{ method.label }}</span>
                        </button>
                    }
                </div>

                <div>
                    <input type="text" [(ngModel)]="reference" placeholder="Referencia / Notas (Opcional)" 
                        (keydown.enter)="confirmPayment($event)"
                        class="w-full px-4 py-3 bg-slate-50 border-transparent focus:bg-white border focus:border-indigo-500 rounded-xl text-sm transition-all outline-none text-slate-700 placeholder:text-slate-400">
                </div>

            </div>

            <div class="p-4 bg-slate-50 border-t border-slate-100 flex gap-3">
                <button (click)="onCancel.emit()" class="flex-1 py-3 font-bold text-slate-500 hover:text-slate-700 transition rounded-xl border border-transparent hover:bg-white hover:border-slate-200">Cancelar (Esc)</button>
                <button (click)="confirmPayment($event)" 
                        [disabled]="!selectedMethod() || paymentAmount <= 0"
                        class="flex-[2] bg-slate-900 text-white rounded-xl font-bold py-3 hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-slate-900/20 active:scale-95 transition-all flex items-center justify-center gap-2">
                    <i class="fas fa-check"></i> Confirmar Pago
                </button>
            </div>
        </div>
    </div>
    `
})
export class PaymentModalComponent implements AfterViewInit {
    @Input() amountUsd: number = 0;
    @Input() amountVes: number = 0;
    @Input() exchangeRate: number = 0;

    @Output() onConfirm = new EventEmitter<{ method: string, amount: number, currency: string, reference?: string }>();
    @Output() onCancel = new EventEmitter<void>();

    // Elementos del DOM para manipular foco
    @ViewChildren('methodBtn') methodBtns!: QueryList<ElementRef>;
    @ViewChild('amountInput') amountInput!: ElementRef;

    currency = signal<'VES' | 'USD'>('VES');
    selectedMethod = signal<string>('');

    reference = '';
    paymentAmount: number = 0; // Propiedad enlazada al input
    focusedIndex = 0; // Para navegación por teclado

    methodsVES = [
        { id: 'CASH', label: 'Efectivo Bs', icon: 'fas fa-money-bill-wave' },
        { id: 'PAGO_MOVIL', label: 'Pago Móvil', icon: 'fas fa-mobile-alt' },
        { id: 'DEBIT_CARD', label: 'T. Débito', icon: 'far fa-credit-card' },
        { id: 'CREDIT_CARD', label: 'T. Crédito', icon: 'fas fa-credit-card' },
        { id: 'BIOPAGO', label: 'Biopago', icon: 'fas fa-fingerprint' },
        { id: 'TRANSFER', label: 'Transferencia', icon: 'fas fa-university' },
        { id: 'OTHERS', label: 'Otros', icon: 'fas fa-ellipsis-h' }
    ];

    methodsUSD = [
        { id: 'CASH', label: 'Efectivo $', icon: 'fas fa-money-bill-1' },
        { id: 'ZELLE', label: 'Zelle', icon: 'fas fa-dollar-sign' },
        { id: 'USDT', label: 'USDT', icon: 'fab fa-bitcoin' },
        { id: 'PAYPAL', label: 'PayPal', icon: 'fab fa-paypal' },
        { id: 'OTHERS', label: 'Otros', icon: 'fas fa-ellipsis-h' }
    ];

    currentMethods = computed(() => this.currency() === 'VES' ? this.methodsVES : this.methodsUSD);

    constructor() {
        // Efecto: Cuando cambia la moneda, actualizamos el monto sugerido
        effect(() => {
        const curr = this.currency();
            // Solo actualizamos si el usuario no ha editado (o podemos forzar reset)
            // Aquí forzamos reset al total correspondiente para evitar errores de cálculo
            const rawAmount = curr === 'VES' ? this.amountVes : this.amountUsd;
            this.paymentAmount = Math.round((rawAmount + Number.EPSILON) * 100) / 100;

            // Resetear selección y foco
            this.selectedMethod.set('');
            this.focusedIndex = 0;

            // Re-enfocar botones después de renderizar (pequeño delay)
            setTimeout(() => this.focusOption(0), 50);
        });
    }

    ngAfterViewInit() {
        // Foco inicial al primer botón de método
        setTimeout(() => this.focusOption(0), 100);
    }

    setCurrency(curr: 'VES' | 'USD') {
        
    }

    // --- NAVEGACIÓN POR TECLADO ---
    @HostListener('window:keydown', ['$event'])
    handleKeyboardEvents(event: KeyboardEvent) {
        // Si el foco está en el input de monto o referencia, permitir comportamiento normal
        // excepto Enter y Escape
        const activeTag = document.activeElement?.tagName;
        if (activeTag === 'INPUT') {
            if (event.key === 'Escape') {
                this.onCancel.emit();
                return;
            }
            // Enter se maneja en el HTML (confirmPayment)
            return; 
        }

        const listLength = this.currentMethods().length;

        switch(event.key) {
            case 'ArrowRight':
                event.preventDefault();
                this.focusOption((this.focusedIndex + 1) % listLength);
                break;
            case 'ArrowLeft':
                event.preventDefault();
                this.focusOption((this.focusedIndex - 1 + listLength) % listLength);
                break;
            case 'ArrowDown':
                event.preventDefault();
                // Salto de línea en grid de 3 columnas (aprox)
                const nextRow = this.focusedIndex + 3;
                if (nextRow < listLength) this.focusOption(nextRow);
                else this.focusOption((this.focusedIndex + 1) % listLength); // Fallback a siguiente
                break;
            case 'ArrowUp':
                event.preventDefault();
                const prevRow = this.focusedIndex - 3;
                if (prevRow >= 0) this.focusOption(prevRow);
                else this.focusOption((this.focusedIndex - 1 + listLength) % listLength);
                break;
            case 'Escape':
                this.onCancel.emit();
            break;
            // F2 para cambiar moneda rápidamente
            case 'F2':
                event.preventDefault();
                this.setCurrency(this.currency() === 'VES' ? 'USD' : 'VES');
                break;
        }
    }

    focusOption(index: number) {
        if (!this.methodBtns) return;

        const buttonArray = this.methodBtns.toArray();
        if (buttonArray[index]) {
            this.focusedIndex = index;
            buttonArray[index].nativeElement.focus();
        }
    }

    // --- LÓGICA DE SELECCIÓN ---

    selectMethod(methodId: string) {
        this.selectedMethod.set(methodId);
        // UX: Al hacer click/seleccionar, llevar foco al monto por si quiere editarlo (pago parcial)
        this.focusAmountInput();
    }

    onEnterOnMethod(methodId: string, event: Event) {
        event.preventDefault();
        this.selectedMethod.set(methodId);
        this.focusAmountInput(true); // Seleccionar texto para sobreescribir rápido
    }

    focusAmountInput(selectAll: boolean = false) {
        setTimeout(() => {
            if (this.amountInput) {
                this.amountInput.nativeElement.focus();
                if (selectAll) this.amountInput.nativeElement.select();
            }
        }, 50);
    }

    confirmPayment(event: Event) {
    event.stopPropagation();

    // Validación básica
    if (this.paymentAmount <= 0) {
        alert('El monto debe ser mayor a 0');
            return;
        }
        if (!this.selectedMethod()) {
            alert('Seleccione un método de pago');
            return;
        }

        this.onConfirm.emit({
            method: this.selectedMethod(),
            amount: this.paymentAmount,
            currency: this.currency(),
            reference: this.reference
        });
    }
}