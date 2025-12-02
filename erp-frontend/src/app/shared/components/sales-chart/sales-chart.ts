import { Component, Input, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartData, ChartType } from 'chart.js';
import { SalesDataPoint } from '../../../core/services/finance';

@Component({
    selector: 'app-sales-chart',
    standalone: true,
    imports: [CommonModule, BaseChartDirective],
    template: `
    <div class="h-[400px] w-full">
      <canvas baseChart
        [data]="chartData()"
        [options]="chartOptions"
        [type]="chartType"
      >
      </canvas>
    </div>
  `
})
export class SalesChartComponent implements OnInit {
    // Propiedad de entrada para recibir los datos del Dashboard
    @Input() salesData: SalesDataPoint[] = [];

    // Configuración de Chart.js
    chartType: ChartType = 'line';

    // Datos reactivos que se pasarán a la librería
    chartData = signal<ChartData<'line'>>({
        labels: [],
        datasets: []
    });

    // Opciones de la gráfica
    chartOptions: ChartConfiguration['options'] = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: { grid: { display: false } },
            y: { ticks: { callback: (val) => '$' + val } }
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: (context) => `Ventas: $${context.formattedValue}`
                }
            }
        }
    };

    ngOnInit() {
        this.processData();
    }

    processData(): void {
        if (!this.salesData || this.salesData.length === 0) return;

        const labels = this.salesData.map(d => d.month);
        const data = this.salesData.map(d => d.sales_usd);

        this.chartData.set({
            labels: labels,
            datasets: [
                {
                    data: data,
                    label: 'Ventas Mensuales (USD)',
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    borderColor: '#3b82f6',
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#3b82f6',
                    fill: 'origin',
                    tension: 0.3
                }
            ]
        });
    }
}
