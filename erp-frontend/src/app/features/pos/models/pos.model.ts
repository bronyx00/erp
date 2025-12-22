export interface Product {
  id: number;
  name: string;
  price: number;
  stock: number;
  category: string;
  sku: string;
  image?: string;
}

export interface CartItem {
  product: Product;
  quantity: number;
}

// Para cuando envie la venta al backend
export interface SalePayload {
  customerId: number | null;
  items: { productId: number; quantity: number }[];
  total: number;
  paymentMethod: 'CASH' | 'CARD' | 'TRANSFER' | 'PAGO MOVIL';
}