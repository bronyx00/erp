import { Injectable, computed, signal } from '@angular/core';
import { Product } from './inventory';
import { SaleTransaction } from './finance';
import type { PaymentMethodType } from '../../features/pos/pos';

export interface CartItem extends Product {
  quantity: number;
  line_total: number;
}

interface CartState {
  items: CartItem[];
  customer_name: string | null;
}

const initialState: CartState = {
  items: [],
  customer_name: 'Consumidor Final'
};

@Injectable({ providedIn: 'root' })
export class CartService {
  // Estado del carrito usando Signal
  private state = signal(initialState);

  // Selectores (Computed Signals)
  items = computed(() => this.state().items);
  customerName = computed(() => this.state().customer_name);
  
  subtotal = computed(() => 
    this.items().reduce((sum, item) => sum + item.line_total, 0)
  );
  taxRate = computed(() => 0.16); // 16% IVA
  taxAmount = computed(() => this.subtotal() * this.taxRate());
  total = computed(() => this.subtotal() + this.taxAmount());


  /**
   * Agrega un producto al carrito o incrementa la cantidad si ya existe.
   */
  addItem(product: Product): void {
    this.state.update(state => {
      const existingItem = state.items.find(item => item.id === product.id);
      
      if (existingItem) {
        existingItem.quantity++;
        existingItem.line_total = existingItem.quantity * existingItem.price;
      } else {
        const newItem: CartItem = {
          ...product,
          quantity: 1,
          line_total: product.price
        };
        state.items.push(newItem);
      }
      
      return { ...state };
    });
  }

  /**
   * Genera el objeto de transacción final con base en el estado actual del carrito
   * y simula el cierre, devolviendo el objeto que se enviaría al backend.
   */
  finalizeTransaction(paymentMethod: PaymentMethodType, amountReceived: number): SaleTransaction {
    const transactionItems = this.items().map(item => ({
      sku: item.sku,
      name: item.name,
      quantity: item.quantity,
      price: item.price,
      line_total: item.line_total,
    }));

    const transaction: SaleTransaction = {
      customer_name: this.customerName() || 'Consumidor Final',
      subtotal: this.subtotal(),
      tax_rate: this.taxRate(),
      tax_amount: this.taxAmount(),
      total_usd: this.total(),
      payment_method: paymentMethod,
      amount_received: amountReceived,
      change_due: amountReceived > this.total() ? amountReceived - this.total() : 0,
      items: transactionItems,
    };

    // Simulación de envío al backend. Aquí se haría el HTTP POST real.
    console.log('--- TRANSACCIÓN COMPLETADA (MOCK) ---');
    console.table(transaction);
    
    // Limpia el carrito después de la venta
    this.clearCart(); 

    return transaction;
  }

  updateQuantity(productId: number, quantity: number): void {
    this.state.update(state => {
      const item = state.items.find(i => i.id === productId);
      if (item) {
        item.quantity = quantity > 0 ? quantity : 1;
        item.line_total = item.quantity * item.price;
      }
      return { ...state };
    });
  }

  removeItem(productId: number): void {
    this.state.update(state => ({
      ...state,
      items: state.items.filter(i => i.id !== productId)
    }));
  }

  clearCart(): void {
    this.state.set(initialState);
  }

  setCustomer(name: string): void {
    this.state.update(state => ({ ...state, customer_name: name }));
  }
}