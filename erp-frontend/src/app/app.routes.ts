import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login';
import { AppLayoutComponent } from './core/layout/app-layout.component';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
  { path: 'login', 
    component: LoginComponent ,
    title: 'ERP - Iniciar Sesión'
  },
  {
    path: '',
    component: AppLayoutComponent, // El Layout envuelve al dashboard
    canActivate: [roleGuard(['OWNER', 'ADMIN', 'MANAGER', 'SELLER', 'CASHIER', 'HHRR', 'COUNTER', 'STORE', 'SECURITY', 'CLEANING'])],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'settings',
        loadComponent: () => import('./features/settings/settings').then(m => m.Settings),
        canActivate: [roleGuard(['OWNER'])]
      },
      { 
        path: 'dashboard', 
        loadComponent: () => import('./features/dashboard/dashboard').then(m => m.DashboardComponent),
        canActivate: [roleGuard(['OWNER', 'ADMIN', 'MANAGER'])],
        title: 'ERP - Dashboard',
      },
      // --- RECURSOS HUMANOS (HHRR) ---
      // Requiere permisos de gestión y hhrr
      {
        path: 'hhrr',
        loadComponent: () => import('./features/employees/employees-detail/employee-detail').then(m => m.EmployeeDetailComponent),
        canActivate: [roleGuard(['OWNER', 'HHRR'])]
      },
      {
        path: 'hhrr/employees',
        loadComponent: () => import('./features/employees/employees').then(m => m.EmployeesComponent),
        canActivate: [roleGuard(['OWNER', 'ADMIN', 'HHRR'])]
      },
      {
        path: 'crm',
        loadComponent: () => import('./features/crm/client-list/client-list.component').then(m => m.ClientListComponent),
        canActivate: [roleGuard(['OWNER', 'ADMIN', 'SELLER'])],
      },
      // --- PUNTO DE VENTA (POS) --- 
      // Requiere permisos de gestión o caja
      {
        path: 'pos',
        loadComponent: () => import('./features/pos/pos-terminal/pos-terminal.component').then(m => m.PosTerminalComponent),
        canActivate: [roleGuard(['OWNER', 'ADMIN', 'CASHIER'])],
        title: 'ERP - Punto de Venta',
      },
      // --- INVENTARIO ---
      // Requiere permisos de gestión o almacén
      {
        path: 'inventory/products',
        loadComponent: () => import('./features/inventory/product-list/product-list').then(m => m.ProductListComponent),
        canActivate: [roleGuard(['OWNER', 'STORE'])]
      },
      {
        path: 'inventory/products/new',
        loadComponent: () => import('./features/inventory/product-form/product-form').then(m => m.ProductFormComponent),
        canActivate: [roleGuard(['OWNER', 'STORE'])],
        title: 'ERP - Nuevo Producto',
      },
      // --- CONTABILIDAD ---
      // Requiere permisos de gestión o contabilidad
      {
        path: 'accounting/expenses',
        loadComponent: () => import('./features/expenses/expense-dashboard/expense-dashboard').then(m => m.ExpenseDashboardComponent),
        canActivate: [roleGuard(['OWNER', 'COUNTER'])],
        title: 'ERP - Control de Gastos',
      },
      {
        path: 'accounting/books',
        loadComponent: () => import('./features/accounting/accounting-books/accounting-books').then(m => m.AccountingBooksComponent),
        canActivate: [roleGuard(['OWNER', 'COUNTER'])]
      },
      {
        path: 'accounting',
        loadComponent: () => import('./features/accounting/accounting-service').then(m => m.AccountingServiceComponent),
        canActivate: [roleGuard(['OWNER', 'ADMIN', 'MANAGER', 'COUNTER'])],
        title: 'ERP - Contabilidad y Finanzas',
      },
      // --- REPORTES ---
      // Requiere permisos de supervición o caja
      {
        path: 'reports/daily-sales',
        loadComponent: () => import('./features/reports/sales-report/sales-report').then(m => m.DailySalesReportComponent),
        canActivate: [roleGuard(['OWNER', 'ADMIN', 'MANAGER', 'CASHIER'])],
        title: 'ERP - Cierre de Caja',
      },
    ]
  },
  { path: '**', redirectTo: 'login' }
];