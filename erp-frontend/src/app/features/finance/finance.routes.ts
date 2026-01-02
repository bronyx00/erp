import { Routes } from '@angular/router';

export const FINANCE_ROUTES: Routes = [
  {
    path: 'invoices',
    loadComponent: () => import('./invoices/invoice-list/invoice-list.component').then(m => m.InvoiceListComponent),
    title: 'Finanzas | Facturas'
  },
  {
    path: 'quotes',
    loadComponent: () => import('./quotes/quote-list/quote-list.component').then(m => m.QuoteListComponent),
    title: 'Finanzas | Cotizaciones'
  },
  {
    path: 'quotes/new',
    loadComponent: () => import('./quotes/quote-form/quote-form.component').then(m => m.QuoteFormComponent),
    title: 'Finanzas | Nueva Cotización'
  },
  {
    path: '',
    redirectTo: 'invoices',
    pathMatch: 'full'
  }
];