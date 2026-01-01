import { Injectable, inject, Inject } from '@angular/core';
import { HttpClient, HttpParams } from "@angular/common/http";
import { Observable, of } from "rxjs";
import { environment } from '../../../environments/environment';

export type PaymentMethod = 'MOBILE_PAYMENT' | 'BIO_PAYMENT' | 'DEBIT_CARD' | 'TRANSFER' | 'CASH' | 'OTHER';

export interface PaginatedResponse<T> {
    data: T[];
    meta: {
        total: number;
        page: number;
        limit: number;
        total_pages: number;
    };
}

// Modelo de ítem de Factura
export interface InvoiceItem {
  product_name: string;
  quantity: number;
  description?: string;
  unit_price: number;
  total_price: number;
}

// Datos para crear la factura
export interface InvoiceItemCreate {
  product_id: number;
  quantity: number;
}

export interface InvoicePaymentCreate {
  amount: number;
  payment_method: PaymentMethod;
  reference?: string;
  notes?: string;
}

export interface InvoiceCreate {
  customer_tax_id: string;
  salesperson_id?: number;
  currency: string;
  items: InvoiceItemCreate[];
  payment?: InvoicePaymentCreate;
}

export interface Invoice {
  id: number;
  invoice_number: number;
  control_number?: string;
  status: 'ISSUED' | 'PAID' | 'PARTIALLY_PAID' | 'VOID';
  
  // Totales
  subtotal_usd: number;
  tax_amount_usd: number;
  total_usd: number;
  
  currency: string;
  exchange_rate?: number;
  amount_ves?: number; 

  // Datos Cliente
  customer_name?: string;
  customer_rif?: string;
  customer_email?: string;
  customer_address?: string; 
  customer_phone?: string;   

  // Datos Empresa 
  company_name?: string;     
  company_rif?: string;      
  company_address?: string;  

  salesperson_id?: number;
  
  items?: InvoiceItem[];
  payments?: Payment[];

  total_paid: number;
  balance_due: number;
  created_at: string;
}

export interface Payment {
    id: number;
    amount: number;
    payment_method: string;
    created_at: string;
    exchange_rate: number;
    currency: string;
    amount_in_usd: number;
    reference?: string;
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
  currency: string;
  payment_method: string;
  reference?: string; 
  notes?: string;
}

// --- COTIZACIONES ---
export interface Quote {
  id: number;
  quote_number: string;
  status: 'DRAFT' | 'SENT' | 'ACCEPTED' | 'REJECTED' | 'INVOICED';
  company_name: string;
  company_rif: string;
  company_address: string;
  customer_name: string;
  customer_rif: string;
  customer_email?: string;
  customer_address?: string;
  customer_phone?: string;
  date_issued: string;
  date_expires: string;
  currency: string;
  subtotal: number;
  tax_amount: number;
  total: number;
  notes?: string;
  terms?: string;
  items: QuoteItem[];
}

export interface QuoteItem {
  product_id: number;
  product_name: string; // Para visualización
  description?: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

export interface QuoteCreate {
  customer_tax_id: string; 
  date_expires: string;
  currency: string;
  items: {
    product_id: number;
    quantity: number;
    unit_price?: number;
    description?: string;
  }[];
  notes?: string;
  terms?: string;
}

// --- CIERRE DE CAJA ---
export interface CashCloseCreate {
    declared_cash_usd: number;
    declared_cash_ves: number;
    declared_card_usd: number; 
    declared_card_ves: number;
    notes?: string;
}

export interface CashCloseResponse {
    id: number;
    period_start: string;
    period_end: string;
    
    // 1. Totales Globales
    total_sales_usd: number;
    total_tax_usd: number;
    total_sales_ves: number;
    total_tax_ves: number;
    
    // Campo calculado 
    total_system_income_usd?: number; 

    // 2. Desglose Sistema USD
    total_cash_usd: number;
    total_debit_card_usd: number;
    total_transfer_usd: number;
    total_credit_sales_usd: number;
    
    // 3. Desglose Sistema VES
    total_cash_ves: number;
    total_debit_card_ves: number;
    total_transfer_ves: number;  
    total_credit_sales_ves: number; 
    
    // 4. Declarado por Usuario
    declared_cash_usd: number;
    declared_cash_ves: number;
    declared_card_usd: number;
    declared_card_ves: number;
    
    // 5. Diferencias
    difference_usd: number;
    difference_ves: number;
    
    created_at: string;
    notes?: string;
}

@Injectable({
  providedIn: 'root'
})
export class FinanceService {
  private http = inject(HttpClient);
  private readonly API_URL = `${environment.apiUrl}/finance`;

  // --- FACTURACIÓN ---
  getInvoices(page: number = 1, limit: number = 20, search?: string, status?: string, startDate?: string, endDate?: string): Observable<PaginatedResponse<Invoice>> {
    let params = new HttpParams()
      .set('page', page)
      .set('limit', limit);

    if (search) params = params.set('search', search);
    if (status) params = params.set('status', status);
    if (startDate) params = params.set('start_date', startDate);
    if (endDate) params = params.set('end_date', endDate);

    return this.http.get<PaginatedResponse<Invoice>>(`${this.API_URL}/invoices`, { params });
  }

  getInvoiceById(id: number): Observable<Invoice> {
    return this.http.get<Invoice>(`${this.API_URL}/invoices/${id}`);
  }

  createInvoice(invoice: InvoiceCreate): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.API_URL}/invoices`, invoice);
  }

  getCurrentRate(): Observable<ExchangeRate> {
    return this.http.get<ExchangeRate>(`${this.API_URL}/exchange-rate`);
  }

  registerPayment(payment: PaymentCreate): Observable<any> {
    return this.http.post(`${this.API_URL}/payments`, payment);
  }

  getInvoicePdf(id: number): Observable<Blob> {
    return this.http.get(`${this.API_URL}/invoices/${id}/pdf`, { responseType: 'blob' });
  }

  voidInvoice(id: number): Observable<any> {
    return this.http.post(`${this.API_URL}/invoices/${id}/void`, {});
  }

  // --- COTIZACIONES ---
  getQuotes(page: number = 1, limit: number = 20, search?: string, status?: string): Observable<any> {
    let params = new HttpParams().set('page', page).set('limit', limit);
    if (search) params = params.set('search', search);
    if (status) params = params.set('status', status);
    return this.http.get(`${this.API_URL}/quotes`, { params });
  }

  createQuote(data: QuoteCreate): Observable<Quote> {
    return this.http.post<Quote>(`${this.API_URL}/quotes`, data);
  }

  convertQuoteToInvoice(quoteId: number): Observable<any> {
    return this.http.post(`${this.API_URL}/quotes/${quoteId}/convert`, {});
  }
  
  // --- CIERRE DE CAJA ---
  performCashClose(data: CashCloseCreate): Observable<CashCloseResponse> {
    return this.http.post<CashCloseResponse>(`${this.API_URL}/cash-close`, data);
  }
}