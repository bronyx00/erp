import { Injectable, inject, computed, signal } from '@angular/core';
import { Product } from './inventory';

export interface CartItem {
  product: Product;
  quantity: number;
}

@Injectable({
  providedIn: 'root',
})
export class CartService {
  // Estado reactivo del carrito
  items = signal<CartItem[]>([]);

  // Cálculo automático del total
  total = computed(() => {
    return this.items().reduce((acc, item) => acc + (item.product.price * item.quantity), 0);
  });

  // Agregar producto (o sumar cantidad si ya existe)
  addToCart(product: Product) {
    this.items.update(currentItems => {
      const existingItem = currentItems.find(i => i.product.id === product.id);
      if (existingItem) {
        return currentItems.map(i =>
          i.product.id === product.id ? { ...i, quantity: i.quantity + 1 } : i
        );
      }
      return [...currentItems, { product, quantity: 1 }];
    });
  }

  // Quitar un ítem completo
  removeFromCart(productId: number) {
    this.items.update(items => items.filter(i => i.product.id !== productId));
  }

  // Modificar cantidad manualmente
  updateQuantity(productId: number, qty: number) {
    if (qty <= 0) {
      this.removeFromCart(productId);
      return;
    }
    this.items.update(items =>
      items.map(i => i.product.id === productId ? { ...i, quantity: qty } : i )
    );
  }

  clear() {
    this.items.set([]);
  }
}
