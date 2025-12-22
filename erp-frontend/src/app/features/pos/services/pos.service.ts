import { Injectable, computed, signal } from '@angular/core';
import { Product, CartItem } from '../models/pos.model';

@Injectable({ providedIn: 'root' })
export class PosService {
  
  // --- STATE SIGNALS ---
  cart = signal<CartItem[]>([]);
  isLoading = signal(false);

  // --- COMPUTED VALUES ---
  // Se recalculan automáticamente. Si el cart cambia, estos números cambian.
  subtotal = computed(() => this.cart().reduce((acc, item) => acc + (item.product.price * item.quantity), 0));
  tax = computed(() => this.subtotal() * 0.16); // IVA 16%
  total = computed(() => this.subtotal() + this.tax());
  totalItems = computed(() => this.cart().reduce((acc, item) => acc + item.quantity, 0));

  // --- ACCIONES ---

  addToCart(product: Product) {
    this.cart.update(items => {
      const existing = items.find(i => i.product.id === product.id);
      if (existing) {
        // Si ya existe, inmutablente creamos un nuevo array actualizando la cantidad
        return items.map(i => i.product.id === product.id 
          ? { ...i, quantity: i.quantity + 1 } 
          : i);
      }
      // Si es nuevo, lo agregamos al array
      return [...items, { product, quantity: 1 }];
    });
  }

  removeFromCart(productId: number) {
    this.cart.update(items => items.filter(i => i.product.id !== productId));
  }

  updateQuantity(productId: number, delta: number) {
    this.cart.update(items => {
      return items.map(i => {
        if (i.product.id === productId) {
          const newQty = i.quantity + delta;
          // Evitamos cantidades negativas o cero desde aquí
          return newQty > 0 ? { ...i, quantity: newQty } : i;
        }
        return i;
      });
    });
  }

  clearCart() {
    this.cart.set([]);
  }

  // Aquí conectarías con tu API real para procesar la venta
  processSale(customerId: number | null) {
    this.isLoading.set(true);
    console.log('Procesando venta para cliente:', customerId, 'Items:', this.cart());
    
    // Simulación de API
    setTimeout(() => {
      this.isLoading.set(false);
      this.clearCart();
      alert('¡Venta registrada con éxito!');
    }, 1500);
  }
}