import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login';
import { RegisterComponent } from './features/auth/register/register.component';
import { AppLayoutComponent } from './core/layout/app-layout.component';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
  { path: 'login', 
    component: LoginComponent ,
    title: 'ERP - Iniciar Sesión'
  },
  { path: 'sign-up', 
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
        loadComponent: () => import('./features/settings/settings').then(m => m.Settings),
        canActivate: [roleGuard(['OWNER'])]
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
        path: 'inventory/products',
        loadComponent: () => import('./features/inventory/product-list/product-list.component').then(m => m.ProductListComponent)
      },
      // --- CONTABILIDAD ---
      // Requiere permisos de gestión o contabilidad
    ]
  },
  { path: '**', redirectTo: 'login' }
];