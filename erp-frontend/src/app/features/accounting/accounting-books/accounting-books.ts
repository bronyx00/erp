import { Component, OnInit } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface JournalEntry {
  id: number;
  date: string;
  code: string; // Código de asiento
  description: string;
  items: {
    account: string;
    accountName: string;
    debit: number;
    credit: number;
  }[];
}

@Component({
  selector: 'app-accounting-books',
  standalone: true,
  imports: [CommonModule, FormsModule, CurrencyPipe, DatePipe],
  templateUrl: './accounting-books.html',
})
export class AccountingBooksComponent implements OnInit {
  activeBook: 'JOURNAL' | 'LEDGER' = 'JOURNAL';
  
  // MOCK DATA: Libro Diario
  journalEntries: JournalEntry[] = [
    {
      id: 1, date: '2025-12-01', code: 'AS-001', description: 'Venta Factura #1001',
      items: [
        { account: '1101', accountName: 'Bancos', debit: 1160.00, credit: 0 },
        { account: '4101', accountName: 'Ingresos por Ventas', debit: 0, credit: 1000.00 },
        { account: '2105', accountName: 'IVA Débito Fiscal', debit: 0, credit: 160.00 },
      ]
    },
    {
      id: 2, date: '2025-12-02', code: 'AS-002', description: 'Pago de Servicios (Luz)',
      items: [
        { account: '5102', accountName: 'Gastos de Servicios', debit: 50.00, credit: 0 },
        { account: '1101', accountName: 'Bancos', debit: 0, credit: 50.00 },
      ]
    }
  ];

  // MOCK DATA: Libro Mayor (Transformado)
  ledgerAccounts = [
    { code: '1101', name: 'Bancos', balance: 50000, movements: [{date: '2025-12-01', ref: 'AS-001', debit: 1160, credit: 0}, {date: '2025-12-02', ref: 'AS-002', debit: 0, credit: 50}] },
    { code: '4101', name: 'Ingresos Ventas', balance: 10000, movements: [{date: '2025-12-01', ref: 'AS-001', debit: 0, credit: 1000}] },
  ];

  ngOnInit() {}
}