import { Component, OnInit, inject } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { FinanceService, AccountingAccount, Invoice, LedgerEntry, AccountType } from '../../core/services/finance';
import { RouterModule } from '@angular/router'; // Necesario para la navegación interna (si aplica)

@Component({
  selector: 'app-accounting-service',
  standalone: true,
  imports: [CommonModule, FormsModule, CurrencyPipe, DatePipe, RouterModule],
  templateUrl: './accounting-service.html',
  styleUrls: ['./accounting-service.scss'], // Aunque usaremos Tailwind, la línea se mantiene
})
export class AccountingServiceComponent implements OnInit {
  private financeService = inject(FinanceService);
  private titleService = inject(Title);

  // Data
  accounts: AccountingAccount[] = [];
  invoices: Invoice[] = [];
  
  // UI State
  isLoading = false;
  activeTab: 'invoices' | 'accounts' | 'ledger' = 'invoices';
  selectedInvoice: Invoice | null = null; // Para mostrar el detalle de la factura
  isInvoiceModalOpen = false;

  // Nuevo Formulario de Asiento Contable
  newEntry: Partial<LedgerEntry> = {
    date: new Date().toISOString().substring(0, 10), // Fecha de hoy
    amount: 0,
    description: '',
    reference: '',
  };
  
  // Opciones para la cuenta (para el select del formulario)
  accountCodes: string[] = [];

  ngOnInit(): void {
    this.titleService.setTitle('ERP - Contabilidad y Finanzas');
    this.loadData();
  }

  loadData(): void {
    this.isLoading = true;
    this.financeService.getInvoices().subscribe(data => {
      this.invoices = data;
      this.isLoading = false;
    });

    this.financeService.getChartOfAccounts().subscribe(data => {
      this.accounts = data;
      this.accountCodes = this.accounts.map(a => `${a.code} - ${a.name}`);
    });
  }

  changeTab(tab: 'invoices' | 'accounts' | 'ledger'): void {
    this.activeTab = tab;
  }

  // --- Facturas ---
  openInvoiceDetail(invoice: Invoice): void {
    this.selectedInvoice = invoice;
    this.isInvoiceModalOpen = true;
  }

  closeInvoiceDetail(): void {
    this.isInvoiceModalOpen = false;
    this.selectedInvoice = null;
  }

  // --- Asientos Contables ---
  
  submitNewEntry(): void {
    if (!this.newEntry.debitAccount || !this.newEntry.creditAccount || !this.newEntry.amount || !this.newEntry.description) {
        alert('Por favor, complete todos los campos requeridos.');
        return;
    }

    if (this.newEntry.debitAccount === this.newEntry.creditAccount) {
        alert('Las cuentas de Débito y Crédito deben ser diferentes.');
        return;
    }

    const entryToSave: LedgerEntry = {
        id: 0, // El ID se asigna en el mock
        date: this.newEntry.date!,
        description: this.newEntry.description!,
        debitAccount: this.newEntry.debitAccount.split(' ')[0]!,
        creditAccount: this.newEntry.creditAccount.split(' ')[0]!,
        amount: this.newEntry.amount!,
        reference: this.newEntry.reference || '',
    };
    
    this.financeService.createLedgerEntry(entryToSave).subscribe(
        (response) => {
            alert(`Asiento Contable #${response.id} creado exitosamente.`);
            // Limpiar formulario y recargar datos si es necesario
            this.newEntry = { date: new Date().toISOString().substring(0, 10), amount: 0, description: '', reference: '' };
        },
        (error) => {
            console.error('Error al crear asiento:', error);
            alert('Hubo un error al guardar el asiento contable.');
        }
    );
  }
}