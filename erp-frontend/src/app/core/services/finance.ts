import { Injectable, inject, Inject } from '@angular/core';
import { HttpClient } from "@angular/common/http";
import { Observable, of } from "rxjs";
import { ApiService } from '../api/api.service';

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

export interface SalesDataPoint {
  month: string;
  sales_usd: number;
}

@Injectable({
  providedIn: 'root'
})
export class FinanceService {
  private api = Inject(ApiService);
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

  // Obtiene las ventas de los últimos 12 meses para la gráfica
  getSalesOverTime(): Observable<SalesDataPoint[]> {
    // return this.api.get<SalesDataPoint[]>('finance/sales-over-time');
    // MOCK temporal
    return of([
      { month: 'Ene', sales_usd: 15000 },
      { month: 'Feb', sales_usd: 22000 },
      { month: 'Mar', sales_usd: 18500 },
      { month: 'Abr', sales_usd: 25000 },
      { month: 'May', sales_usd: 31000 },
      { month: 'Jun', sales_usd: 35000 },
      { month: 'Jul', sales_usd: 28000 },
      { month: 'Ago', sales_usd: 42000 },
      { month: 'Sep', sales_usd: 39500 },
      { month: 'Oct', sales_usd: 45000 },
      { month: 'Nov', sales_usd: 50500 },
      { month: 'Dic', sales_usd: 62000 }
    ]);
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