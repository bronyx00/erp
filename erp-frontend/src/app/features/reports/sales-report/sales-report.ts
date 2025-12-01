import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FinanceService, SalesReportItem  } from '../../../core/services/finance';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-sales-report',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './sales-report.html',
  styleUrls: ['./sales-report.scss']
})
export class SalesReportComponent implements OnInit {
  private financeService = inject(FinanceService);
  
  // Usamos signals para TODO el estado reactivo
  reportData = signal<SalesReportItem[]>([]);
  isLoading = signal<boolean>(true); // Signal en lugar de variable simple
  totalUSD = signal<number>(0);

  ngOnInit() {
    console.log('Iniciando petición de reporte...'); // Debug

    this.financeService.getSalesReport().subscribe({
      next: (data) => {
        console.log('Datos recibidos:', data); // Verás esto en la consola del navegador (F12)
        
        this.reportData.set(data);
        
        // Calcular total asegurando que sea número (Number())
        const total = data
          .filter(i => i.currency === 'USD')
          .reduce((acc, curr) => acc + Number(curr.total_amount), 0);
          
        this.totalUSD.set(total);
        this.isLoading.set(false); // Actualizamos el signal para quitar el "Cargando"
      },
      error: (e) => {
        console.error('Error en el reporte:', e);
        this.isLoading.set(false);
        alert('Error cargando el reporte. Revisa la consola del navegador.');
      }
    });
  }
}