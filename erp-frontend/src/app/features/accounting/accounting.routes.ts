import { Routes } from '@angular/router';

export const ACCOUNTING_ROUTES: Routes = [
  {
    path: 'chart-of-accounts',
    loadComponent: () => import('./chart-of-accounts/chart-of-accounts.component').then(m => m.ChartOfAccountsComponent),
    title: 'Contabilidad | Plan de Cuentas'
  },/** 
  {
    path: 'journal',
    loadComponent: () => import('./journal/journal-list.component').then(m => m.JournalListComponent),
    title: 'Contabilidad | Libro Diario'
  },
  {
    path: 'reports',
    loadComponent: () => import('./reports/financial-reports.component').then(m => m.FinancialReportsComponent),
    title: 'Contabilidad | Reportes Financieros'
  },*/
  {
    path: '',
    redirectTo: 'chart-of-accounts',
    pathMatch: 'full'
  }
];