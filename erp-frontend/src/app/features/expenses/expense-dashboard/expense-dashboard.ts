import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ExpenseService, Expense, ExpenseReportStats } from '../../../core/services/expense';

@Component({
  selector: 'app-expense-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, CurrencyPipe, DatePipe],
  templateUrl: './expense-dashboard.html',
})
export class ExpenseDashboardComponent implements OnInit {
  private expenseService = inject(ExpenseService);

  expenses = signal<Expense[]>([]);
  stats = signal<ExpenseReportStats>({ to_submit: 0, to_approve: 0, to_pay: 0 });
  isModalOpen = false;
  
  // Modelo para nuevo gasto
  newExpense: Expense = { 
    id: 5,
    date: new Date().toISOString().split('T')[0], 
    currency: 'USD', 
    is_billable: false,
    description: '',
    category: '',
    amount: 0,
    tax_amount: 0,
    total_amount: 0,
    employee_name: '',
    status: 'DRAFT'
  };

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.expenseService.getExpenses().subscribe(data => this.expenses.set(data));
    this.expenseService.getStats().subscribe(data => this.stats.set(data));
  }

  openCreateModal() { this.isModalOpen = true; }
  closeModal() { this.isModalOpen = false; }

  // Simula la subida de un archivo (Recibo)
  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      // En un caso real, aquí subirías el archivo al backend y obtendrías la URL
      this.newExpense.receipt_url = 'assets/mock-receipt.png'; // Mock URL
      console.log('Archivo seleccionado:', file.name);
    }
  }

  saveExpense() {
    this.expenseService.createExpense(this.newExpense).subscribe(() => {
      this.loadData();
      this.closeModal();
      this.newExpense = { 
        id: 5,
        date: new Date().toISOString().split('T')[0], 
        currency: 'USD', 
        is_billable: false,
        description: 'Gasto comin',
        category: 'Gastos operativos',
        amount: 1500,
        tax_amount: 150,
        total_amount: 1650,
        employee_name: 'Carla',
        status: 'DRAFT'
      };
    });
  }

  getStatusColor(status: string): string {
    switch(status) {
      case 'DRAFT': return 'bg-gray-100 text-gray-700';
      case 'SUBMITTED': return 'bg-blue-100 text-blue-700';
      case 'APPROVED': return 'bg-green-100 text-green-700';
      case 'PAID': return 'bg-purple-100 text-purple-700';
      case 'REFUSED': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100';
    }
  }
}