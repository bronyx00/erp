import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";

// Modelo de ítem de Factura
export interface InvoiceItem {
  product_name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

// Datos para crear la factura
export interface InvoiceItemCreate {
  product_id: number;
  quantity: number;
}

export interface InvoiceCreate {
  customer_tax_id: string;
  currency: string;
  items: InvoiceItemCreate[];
}

export interface Invoice {
  id: number;
  invoice_number: number;
  control_number?: number
  status: string;

  subtotal_usd: number;
  tax_amount_usd: number;
  total_usd: number;

  currency: string;
  amount_ves?: number;
  exchange_rate: number;

  customer_name?: string;
  customer_rif?: string;
  customer_email?: string;

  created_at?: string;
  items?: InvoiceItem[];
  payments?: any[];
}

export interface ExchangeRate {
  currency: string;
  rate: number;
  source: string;
  acquired_at?: string;
}

export interface PaymentCreate {
  invoice_id: number;
  amount: number;
  payment_method: string;
  reference?: string;
  notes?: string;
}

export interface SalesReportItem {
  date: string;
  payment_method: string;
  currency: string;
  total_amount: number;
  transaction_count: number;
}

export interface DashboardMetrics {
  today_sales: number;
  month_sales: number;
  pending_balance: number;
  total_invoices_today: number;
}

@Injectable({
  providedIn: 'root'
})
export class FinanceService {
  private http = inject(HttpClient);
  private readonly API_URL = 'http://localhost:80/api/finance';

  // Obtener todas las facturas
  getInvoices(): Observable<Invoice[]> {
    return this.http.get<Invoice[]>(`${this.API_URL}/invoices`);
  }

  // Obtener las metricas
  getMetrics(): Observable<DashboardMetrics> {
    return this.http.get<DashboardMetrics>(`${this.API_URL}/reports/dashboard`);
  }

  getSalesReport(): Observable<SalesReportItem[]> {
    return this.http.get<SalesReportItem[]>(`${this.API_URL}/reports/sales-by-method`);
  }

  // Crear una factura nueva
  createInvoice(invoice: InvoiceCreate): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.API_URL}/invoices`, invoice);
  }

  createPayment(payment: PaymentCreate): Observable<any> {
    return this.http.post(`${this.API_URL}/payments`, payment);
  }

  getInvoicePdf(id: number): Observable<Blob> {
    return this.http.get(`${this.API_URL}/invoices/${id}/pdf`, { responseType: 'blob' });
  }

  voidInvoice(id: number, supervisorToken?: string): Observable<any> {
    let headers = {};
    if (supervisorToken) {
      headers = { 'X-Supervisor-Token': supervisorToken };
    }
    return this.http.post(`${this.API_URL}/invoices/${id}/void`, {}, { headers });
  }

  // Obtener la tada del día
  getCurrentRate(): Observable<ExchangeRate> {
    return this.http.get<ExchangeRate>(`${this.API_URL}/exchange-rate`);
  }
}