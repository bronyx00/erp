import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InvoiceStore } from '../invoicing/services/invoice.store'; 
import { FinanceService, DashboardMetrics, ExchangeRate, SalesDataPoint } from '../../core/services/finance';
import { SalesChartComponent } from '../../shared/components/sales-chart/sales-chart';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, SalesChartComponent],
  templateUrl: './dashboard.html',
})
export class DashboardComponent implements OnInit {
  // Inyectamos el Store (para la tabla) y el Service (para métricas simples)
  readonly store = inject(InvoiceStore);
  private financeService = inject(FinanceService);

  // Estado local para los números de arriba
  metrics = signal<DashboardMetrics | null>(null);
  rate = signal<ExchangeRate | null>(null);
  salesOverTime = signal<SalesDataPoint[]>([]);


  ngOnInit() {
    // 1. Cargar la lista de facturas
    this.store.loadInvoices();

    // 2. Cargar KPIs
    this.financeService.getMetrics().subscribe(data => this.metrics.set(data));
    this.financeService.getCurrentRate().subscribe(data => this.rate.set(data));

    // 3. Cargar datos de la gráfica
    this.financeService.getSalesOverTime().subscribe(data => this.salesOverTime.set(data));
  }
}