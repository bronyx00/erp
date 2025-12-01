import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InvoiceStore } from '../invoicing/services/invoice.store'; // Verifica la ruta
import { FinanceService, DashboardMetrics, ExchangeRate } from '../../core/services/finance';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.html',
})
export class DashboardComponent implements OnInit {
  // Inyectamos el Store (para la tabla) y el Service (para métricas simples)
  readonly store = inject(InvoiceStore);
  private financeService = inject(FinanceService);

  // Estado local para los números de arriba
  metrics = signal<DashboardMetrics | null>(null);
  rate = signal<ExchangeRate | null>(null);

  ngOnInit() {
    // 1. Cargar la lista de facturas
    this.store.loadInvoices();

    // 2. Cargar KPIs
    this.financeService.getMetrics().subscribe(data => this.metrics.set(data));
    this.financeService.getCurrentRate().subscribe(data => this.rate.set(data));
  }
}