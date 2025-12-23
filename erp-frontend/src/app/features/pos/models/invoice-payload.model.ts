import type { PaymentMethod } from "../../../core/services/finance";

export interface InvoiceCreatePayload {
  customer_tax_id: string | null;  // "V-123456" o "GENERICO"
  salesperson_id?: number; // 0 o null
  currency: 'USD' | 'VES';
  items: {
    product_id: number;
    quantity: number;
  }[];
  payment: {
    amount: number;
    payment_method: PaymentMethod;
    reference?: string;
    notes?: string;
  };
}