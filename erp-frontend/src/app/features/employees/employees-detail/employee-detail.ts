import { Component, OnInit, inject } from '@angular/core';
import { CommonModule, DatePipe, CurrencyPipe } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { HhrrService, Employee } from '../../../core/services/hhrr'; 
import { Title } from '@angular/platform-browser';
import { switchMap, of } from 'rxjs';

@Component({
  selector: 'app-employee-detail',
  standalone: true,
  imports: [CommonModule, DatePipe, CurrencyPipe, RouterModule],
  templateUrl: './employee-detail.html', 
  styleUrl: './employee-detail.scss',
})
export class EmployeeDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private hhrrService = inject(HhrrService);
  private titleService = inject(Title);

  employee: Employee | null = null;
  isLoading = true;
  error: string | null = null;
  
  activeTab: 'personal' | 'employment' | 'compensation' | 'performance' | 'documents' = 'personal';

  ngOnInit(): void {
    this.route.paramMap.pipe(
        switchMap(params => {
            const id = 101;
            if (id) {
                this.titleService.setTitle(`ERP - Empleado #\${id}`);
                return this.hhrrService.getEmployeeDetail(id);
            }
            this.error = 'ID de empleado no especificado.';
            return of(undefined);
        })
    ).subscribe(
        (data) => {
            this.isLoading = false;
            if (data) {
                this.employee = data;
                this.titleService.setTitle(`ERP - \${data.fullName}`);
            } else if (!this.error) {
                this.error = 'Empleado no encontrado';
            }
        },
        (err) => {
            this.isLoading = false;
            this.error = 'Error al cargar los datos del empleado.';
        }
    );
  }

  getMonthOfService(hired_at: string | undefined): string {
    if (!hired_at) return 'N/A';

    const hireTimestamp = new Date(hired_at).getTime();
    const nowTimestamp = Date.now();

    // Cálculo de la diferencia en años
    const diffTime = Math.abs(nowTimestamp - hireTimestamp);
    const diffYear = diffTime / (1000 * 60 * 60 * 24 * 365.25);
    const diffMonth = diffTime / (1000 * 60 * 60 * 24 * 30);

    return diffMonth.toFixed(1);
  }

  getStatusClass(status: string): string {
    switch(status) {
        case 'Active': return 'bg-green-100 text-green-800';
        case 'On Leave': return 'bg-yellow-100 text-yellow-800';
        case 'Terminated': return 'bg-red-100 text-red-800';
        default: return 'bg-gray-100 text-gray-800';
        }
    }

  getRatingStars(rating: number): string {
        const fullStars = '⭐'.repeat(rating);
        const emptyStars = '☆'.repeat(5 - rating);
        return fullStars + emptyStars;
    }
}