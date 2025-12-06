// En src/app/features/reports/sales-report/sales-report.ts

import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { FinanceService, DailySalesReport } from '../../../core/services/finance';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-sales-report',
  standalone: true,
  imports: [CommonModule, CurrencyPipe, DatePipe, FormsModule],
  templateUrl: './sales-report.html',
  styleUrls: ['./sales-report.scss']
})
export class DailySalesReportComponent implements OnInit {
  private financeService = inject(FinanceService);
  
  report = signal<DailySalesReport | null>(null);
  isLoading = signal(true);
  
  // Para la selección de fecha
  selectedDate: string = new Date().toISOString().split('T')[0]; // Fecha de hoy en formato YYYY-MM-DD

  ngOnInit(): void {
    this.loadReport(this.selectedDate);
  }

  loadReport(date: string): void {
    this.isLoading.set(true);
    this.report.set(null); // Limpiar el reporte anterior
    
    this.financeService.getDailySalesReport(date).subscribe(data => {
      this.report.set(data);
      this.isLoading.set(false);
    });
  }
  
  // Maneja el cambio de fecha en el input
  onDateChange(): void {
    this.loadReport(this.selectedDate);
  }

  // Helper para obtener el nombre legible del método de pago
  getMethodLabel(method: string): string {
    const map: Record<string, string> = {
      CASH: 'Efectivo',
      CARD: 'Tarjeta de Débito/Crédito',
      TRANSFER: 'Transferencia Bancaria',
      MOBILE_PAYMENT: 'Pago Móvil',
      OTHER: 'Otro/Crédito'
    };
    return map[method] || method;
  }
}