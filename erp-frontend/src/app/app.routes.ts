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
        path: 'dashboard', 
        loadComponent: () => import('./features/dashboard/dashboard').then(m => m.DashboardComponent),
        canActivate: [roleGuard(['OWNER', 'ADMIN', 'MANAGER'])],
        title: 'ERP - Dashboard',
      },
      // --- RECURSOS HUMANOS (HHRR) ---
      // Requiere permisos de gestión y hhrr
      {
        path: 'hhrr/employees',
        loadComponent: () => import('./features/employees/employees').then(m => m.EmployeesComponent),
        canActivate: [roleGuard(['OWNER', 'ADMIN', 'HHRR'])]
      },
      {
        path: 'crm',
        loadComponent: () => import('./features/crm/client-management/client-management').then(m => m.ClientManagementComponent),
        canActivate: [roleGuard(['OWNER', 'ADMIN', 'SELLER'])],
      },
      // --- PUNTO DE VENTA (POS) --- 
      // Requiere permisos de gestión o caja
      {
        path: 'pos',
        loadComponent: () => import('./features/pos/pos').then(m => m.PosComponent),
        canActivate: [roleGuard(['OWNER', 'ADMIN', 'CASHIER'])],
        title: 'ERP - Punto de Venta',
      },
      // --- INVENTARIO ---
      // Requiere permisos de gestión o almacén
      {
        path: 'inventory/products/new',
        loadComponent: () => import('./features/inventory/product-form/product-form').then(m => m.ProductFormComponent),
        canActivate: [roleGuard(['OWNER', 'ADMIN', 'MANAGER', 'STORE'])],
        title: 'ERP - Nuevo Producto',
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