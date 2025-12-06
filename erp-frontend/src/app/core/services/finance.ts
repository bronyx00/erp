import { Injectable, inject, Inject } from '@angular/core';
import { HttpClient } from "@angular/common/http";
import { Observable, of } from "rxjs";
import { ApiService } from '../api/api.service';
import type { PaymentMethodType } from '../../features/pos/pos';

// Modelo de un Item de Pago Individual
export interface PaymentDetail {
  method: PaymentMethodType;
  amount: number;
}

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

// Modelo de una Factura Simplificada para el Reporte
export interface DailyInvoice {
  id: number;
  invoice_number: string;
  created_at: string;
  total_usd: number;
  // amount_ves: number;
  payments: PaymentDetail[];
  seller_name: string;
}

// Modelo del Reporte de Cierre de Caja
export interface DailySalesReport {
  date: string;
  total_sales_usd: number;
  total_invoices: number;
  summary_by_method: Record<PaymentDetail['method'], number>;
  invoices: DailyInvoice[];
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

export interface SaleTransaction {
  customer_name: string;
  subtotal: number;
  tax_rate: number;
  tax_amount: number;
  total_usd: number;
  payment_method: PaymentMethodType;
  amount_received: number;   // Monto que el cliente entrega
  change_due: number;       // Cambio a devolver
  items: {
    sku: string;
    name: string;
    quantity: number;
    price: number;
    line_total: number;
  }[];
}

// MOCK DATA para el reporte
const MOCK_REPORT: DailySalesReport = {
  date: new Date().toISOString().split('T')[0],
  total_sales_usd: 1545.50,
  total_invoices: 10,
  summary_by_method: {
    EFECTIVO: 550.00,
    "TARJETA DEBITO": 750.50,
    TRANSFERENCIA: 245.00,
    "PAGO MOVIL": 89.00,
    OTROS: 0.00
  },
  invoices: [
    { id: 1, invoice_number: '001-001-0001', created_at: new Date().toISOString(), total_usd: 150.00, seller_name: 'Carlos López', payments: [{ method: 'EFECTIVO', amount: 150.00 }] },
    { id: 2, invoice_number: '001-001-0002', created_at: new Date().toISOString(), total_usd: 500.50, seller_name: 'Carlos López', payments: [{ method: 'TARJETA DEBITO', amount: 500.50 }] },
    { id: 3, invoice_number: '001-001-0003', created_at: new Date().toISOString(), total_usd: 300.00, seller_name: 'Ana Pérez', payments: [{ method: 'EFECTIVO', amount: 100.00 }, { method: 'TARJETA DEBITO', amount: 200.00 }] },
    // ... más facturas mockeadas
  ]
};

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

  /**
   * Obtiene el reporte de ventas diarias por método de pago.
   */
  getDailySalesReport(date: string): Observable<DailySalesReport> {
    // return this.http.get<DailySalesReport>(`${this.API_URL}/reports/daily-sales?date=${date}`); // Real
    console.log(`Mock: Solicitando reporte para la fecha ${date}`);
    return of(MOCK_REPORT);
  }

  // Obtener la tada del día
  getCurrentRate(): Observable<ExchangeRate> {
    return this.http.get<ExchangeRate>(`${this.API_URL}/exchange-rate`);
  }
}