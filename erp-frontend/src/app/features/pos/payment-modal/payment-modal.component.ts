import { Component, ElementRef, EventEmitter, Input, Output, QueryList, ViewChildren, HostListener, signal, effect } from '@angular/core';
import { CommonModule, CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import type { PaymentMethod } from '../../../core/services/finance';

interface PaymentOption {
  id: PaymentMethod;
  label: string;
  icon: string;
  color: string;
}

@Component({
  selector: 'app-payment-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, CurrencyPipe],
  template: `
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm transition-opacity">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        <div class="bg-slate-50 border-b border-slate-200 p-6 flex justify-between items-center">
          <div>
            <h2 class="text-2xl font-bold text-slate-800">Confirmar Pago</h2>
            <p class="text-slate-500 text-sm">Use flechas ↑↓ para navegar, ENTER para seleccionar</p>
          </div>
          <div class="text-right">
            <p class="text-xs font-semibold text-slate-500 uppercase">Total a Pagar</p>
            <div class="flex flex-col items-end leading-none">
                <span class="text-3xl font-extrabold text-indigo-600">
                    Bs. {{ totalAmount * exchangeRate | number:'1.2-2' }}
                </span>
                <span class="text-sm font-bold text-slate-400 mt-1">
                    Ref: {{ totalAmount | currency:'USD' }}
                </span>
            </div>
          </div>
        </div>

        <div class="p-6 overflow-y-auto">
          <div class="grid grid-cols-1 gap-3">
            @for (method of methods; track method.id) {
              <div class="relative group">
                <button #methodBtn
                  (click)="selectMethod(method.id)"
                  (keydown.enter)="onEnterOnMethod(method.id, $event)"
                  [class.ring-2]="selectedMethod() === method.id"
                  [class.ring-indigo-500]="selectedMethod() === method.id"
                  [class.bg-indigo-50]="selectedMethod() === method.id"
                  class="w-full flex items-center p-4 border rounded-xl hover:bg-slate-50 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-300 text-left">
                  
                  <div [class]="method.color + ' h-12 w-12 rounded-full flex items-center justify-center text-white text-xl shadow-sm'">
                    <i [class]="method.icon"></i>
                  </div>
                  
                  <div class="ml-4 flex-1">
                    <h3 class="font-bold text-slate-700">{{ method.label }}</h3>
                    <p class="text-xs text-slate-400">Presiona ENTER para asignar total</p>
                  </div>

                  @if (selectedMethod() === method.id) {
                    <div class="ml-4 animate-in fade-in slide-in-from-right-4 duration-200">
                      <input #amountInput
                             type="number" 
                             [(ngModel)]="paymentAmount" 
                             (keydown.enter)="confirmPayment($event)"
                             class="w-40 text-right font-bold text-lg border-b-2 border-indigo-500 bg-transparent focus:outline-none p-1"
                             placeholder="0.00"
                             autofocus>
                    </div>
                  }
                </button>
              </div>
            }
          </div>
        </div>

        <div class="bg-slate-50 p-4 border-t border-slate-200 flex justify-between items-center">
          <p class="text-xs text-slate-400">
            <span class="font-bold border border-slate-300 rounded px-1">ESC</span> Cancelar
            <span class="mx-2">|</span>
            <span class="font-bold border border-slate-300 rounded px-1">ENTER</span> Confirmar
          </p>
          <button (click)="onCancel.emit()" class="px-6 py-2 text-slate-600 font-medium hover:bg-slate-200 rounded-lg transition">
            Cancelar
          </button>
        </div>
      </div>
    </div>
  `
})
export class PaymentModalComponent {
  @Input({ required: true }) totalAmount!: number;
  @Input() exchangeRate: number = 0;
  @Output() onConfirm = new EventEmitter<{ method: PaymentMethod; amount: number }>();
  @Output() onCancel = new EventEmitter<void>();

  @ViewChildren('amountInput') amountInputs!: QueryList<ElementRef>;
  @ViewChildren('methodBtn') methodBtns!: QueryList<ElementRef>;

  selectedMethod = signal<PaymentMethod | null>(null);
  paymentAmount = 0;
  focusedIndex = 0;

  methods: PaymentOption[] = [
    { id: 'MOBILE_PAYMENT', label: 'Pago Móvil', icon: 'fas fa-mobile-alt', color: 'bg-purple-500' },
    { id: 'BIO_PAYMENT', label: 'Bio Pago', icon: 'fas fa-fingerprint', color: 'bg-blue-500' },
    { id: 'DEBIT_CARD', label: 'Tarjeta Débito/Crédito', icon: 'far fa-credit-card', color: 'bg-emerald-500' },
    { id: 'TRANSFER', label: 'Transferencia', icon: 'fas fa-university', color: 'bg-slate-600' },
    { id: 'OTHER', label: 'Otros / Mixto', icon: 'fas fa-wallet', color: 'bg-orange-500' },
  ];

  ngAfterViewInit() {
    // Foco inicial al primer elemento
    setTimeout(() => this.focusOption(0), 100);
  }

  // --- KEYBOARD NAVIGATION ---
  @HostListener('window:keydown', ['$event'])
  handleKeyboardEvents(event: KeyboardEvent) {
    // Si el foco está en el input de monto, no interferimos con las flechas
    if (document.activeElement?.tagName === 'INPUT') return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.focusOption((this.focusedIndex + 1) % this.methods.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      // Lógica para volver al último si estamos en el primero
      const nextIndex = (this.focusedIndex - 1 + this.methods.length) % this.methods.length;
      this.focusOption(nextIndex);
    } else if (event.key === 'Escape') {
        this.onCancel.emit();
    }
  }

  focusOption(index: number) {
    this.focusedIndex = index;
    const buttonArray = this.methodBtns.toArray();
    if (buttonArray[index]) {
      buttonArray[index].nativeElement.focus();
    }
  }

  // --- LÓGICA DE SELECCIÓN ---

  selectMethod(method: PaymentMethod) {
    // Si ya está seleccionado, no hacemos nada para no resetear el input
    if (this.selectedMethod() === method) return;

    this.selectedMethod.set(method);
    // UX: Al hacer click, no pre-llenamos el monto, dejamos que el usuario escriba
    this.focusAmountInput();
  }

  onEnterOnMethod(method: PaymentMethod, event: Event) {
    event.preventDefault();
    this.selectedMethod.set(method);
    this.paymentAmount = this.totalAmount; // UX: Enter pre-llena el monto total
    this.focusAmountInput(true); // True para seleccionar el texto
  }

  focusAmountInput(selectAll: boolean = false) {
    setTimeout(() => {
      const input = this.amountInputs.first;
      if (input) {
          input.nativeElement.focus();
          if (selectAll) input.nativeElement.select();
      }
    }, 50);
  }

    confirmPayment(event: Event) {
        event.stopPropagation();
        if (this.paymentAmount > 0 && this.selectedMethod()) {
            this.onConfirm.emit({
            method: this.selectedMethod()!,
            amount: this.paymentAmount
        });
        }
    }
}