import { Component, inject, signal, computed } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { InventoryService, Product } from '../../core/services/inventory';
import { CartService, CartItem } from '../../core/services/cart';
import { HotkeysService } from "../../core/services/hotkeys";
import { finalize } from "rxjs";

export type PaymentMethodType = 'EFECTIVO' | 'TARJETA DEBITO' | 'PAGO MOVIL' | 'TRANSFERENCIA' | 'OTROS';

@Component({
  selector: 'app-pos',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './pos.html',
})
export class PosComponent {
  // Inyección de Servicios
  private inventoryService = inject(InventoryService);
  public cartService = inject(CartService);
  private hotkeysService = inject(HotkeysService);

  // Estado Local de la UI
  searchQuery = signal('');
  searchResults = signal<Product[]>([]);
  isSearching = signal(false);
  isPaymentModalOpen = signal(false);
  paymentAmount = signal(0); // Monto que el cliente entrega
  paymentMethod = signal<PaymentMethodType>('TARJETA DEBITO');

  cartItems = this.cartService.items;
  cartTotal = this.cartService.total;
  cartSubtotal = this.cartService.subtotal;
  cartTax = this.cartService.taxAmount;
  customerName = this.cartService.customerName;

  // Computed para calcular el cambio
  changeDue = computed(() => {
    const received = this.paymentAmount();
    const total = this.cartTotal();
    return received > total ? received - total : 0;
  });

  // Lógica de Búsqueda
  onSearch(): void {
    const query = this.searchQuery();
    if (query.length < 3) {
      this.searchResults.set([]);
      return;
    }

    this.isSearching.set(true);
    this.inventoryService.searchProducts(query)
      .pipe(finalize(() => this.isSearching.set(false)))
      .subscribe(results => {
        this.searchResults.set(results);
      });
  }

  // Lógica de Carrito
  addToCart(product: Product): void {
    this.cartService.addItem(product);
    // Opcional: Limpiar búsqueda y enfocarse en la siguiente operación
    this.searchQuery.set('');
    this.searchResults.set([]);
  }

  updateItemQuantity(item: CartItem, event: Event): void {
    const input = event.target as HTMLInputElement;
    const quantity = parseInt(input.value, 10);
    this.cartService.updateQuantity(item.id, quantity);
  }

  // Lógica de Checkout
  checkout(): void {
    if (this.cartTotal() > 0) {
      this.paymentAmount.set(this.cartTotal()); // Sugiere el total por defecto
      this.isPaymentModalOpen.set(true);
    } else {
      alert('El carrito está vacío.');
    }
  }

  processPayment(): void {
    const received = this.paymentAmount();
    const total = this.cartTotal();

    if (received < total) {
      alert('Error: El monto recibido es menor al total.');
      return;
    }

    try {
      const transaction = this.cartService.finalizeTransaction(
        this.paymentMethod(),
        received
      );

      this.closePaymentModal();
      
    } catch (error) {
      console.error('Error al procesar el pago (Mock):', error);
      alert('Ocurrió un error al procesar el pago.');
    }
  }

  setPaymentMethod(method: string): void {
    this.paymentMethod.set(method as PaymentMethodType)
  }

  closePaymentModal(): void {
    this.isPaymentModalOpen.set(false);
    this.paymentAmount.set(0);
    this.paymentMethod.set('TARJETA DEBITO');
  }

  focusSearch(): void {
    console.log('Foco en el campo de búsqueda (F1)');
  }
}