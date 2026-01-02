import { Routes } from '@angular/router';
import { AppLayoutComponent } from './core/layout/app-layout.component';

export const routes: Routes = [
  // --- AUTH FLOW ---
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth.routes').then(m => m.AUTH_ROUTES)
  },

  // --- APP SHELL ---
  {
    path: '',
    component: AppLayoutComponent,
    // canActivate: [AuthGuard], // Descomentar cuando tenga el Guard
    children: [
      /** 
      // 1. Dashboard Principal
      {
        path: 'dashboard',
        loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
        title: 'ERP | Resumen'
      },*/

      // 2. CONTABILIDAD (Agrupado)
      {
        path: 'accounting',
        loadChildren: () => import('./features/accounting/accounting.routes').then(m => m.ACCOUNTING_ROUTES)
      },

      // 3. FINANZAS (Agrupado)
      {
        path: 'finance',
        loadChildren: () => import('./features/finance/finance.routes').then(m => m.FINANCE_ROUTES)
      },

      // 4. CRM
      {
        path: 'crm',
        loadComponent: () => import('./features/crm/client-list/client-list.component').then(m => m.ClientListComponent),
        title: 'ERP | CRM'
      },

      // 5. INVENTARIO
      {
        path: 'inventory',
        loadComponent: () => import('./features/inventory/product-list/product-list.component').then(m => m.ProductListComponent),
        title: 'ERP | Inventario'
      },

      // 6. POS
      {
        path: 'pos',
        loadComponent: () => import('./features/pos/pos-terminal/pos-terminal.component').then(m => m.PosTerminalComponent),
        title: 'ERP | POS'
      },

      // 7. RRHH (Antes HHRR)
      {
        path: 'hr',
        loadComponent: () => import('./features/employees/employees.component').then(m => m.EmployeesComponent),
        title: 'ERP | Recursos Humanos'
      },

      // 8. CONFIGURACIÓN
      {
        path: 'settings',
        loadComponent: () => import('./features/settings/settings').then(m => m.Settings),
        title: 'ERP | Configuración'
      },

      // Redirección por defecto dentro del Shell
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
    ]
  },

  // --- REDIRECCIONES GLOBALES ---
  { path: '', redirectTo: 'auth/login', pathMatch: 'full' },
  { path: '**', redirectTo: 'auth/login' }
];