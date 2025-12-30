import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login';
import { RegisterComponent } from './features/auth/register/register.component';
import { AppLayoutComponent } from './core/layout/app-layout.component';

export const routes: Routes = [
  { path: 'login', 
    component: LoginComponent ,
    title: 'ERP - Iniciar Sesión'
  },
  { path: 'register', 
    component: RegisterComponent ,
    title: 'ERP - Crea tu cuenta'
  },
  {
    path: '',
    component: AppLayoutComponent,
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'settings',
        loadComponent: () => import('./features/settings/settings').then(m => m.Settings)
      },
      {
        path: 'hhrr',
        loadComponent: () => import('./features/employees/employees.component').then(m => m.EmployeesComponent)

      },
      {
        path: 'crm',
        loadComponent: () => import('./features/crm/client-list/client-list.component').then(m => m.ClientListComponent)
      },
      // --- PUNTO DE VENTA (POS) --- 
      // Requiere permisos de gestión o caja
      {
        path: 'pos',
        loadComponent: () => import('./features/pos/pos-terminal/pos-terminal.component').then(m => m.PosTerminalComponent),
        title: 'ERP - Punto de Venta',
      },
      // --- INVENTARIO ---
      // Requiere permisos de gestión o almacén
      {
        path: 'inventory',
        loadComponent: () => import('./features/inventory/product-list/product-list.component').then(m => m.ProductListComponent)
      },
      // --- CONTABILIDAD ---
      // Requiere permisos de gestión o contabilidad

      // --- FINANZAS ---
      {
        path: 'finance/invoices',
        loadComponent: () => import('./features/finance/invoices/invoice-list/invoice-list.component').then(m => m.InvoiceListComponent)
      }
    ]
  },
  { path: '**', redirectTo: 'login' }
];