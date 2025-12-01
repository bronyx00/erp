import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login';
import { DashboardComponent } from './features/dashboard/dashboard';
import { PosComponent } from './features/pos/pos';
import { TeamComponent } from './features/team/team';
import { EmployeesComponent } from './features/employees/employees';
import { ProductFormComponent } from './features/inventory/product-form/product-form';
import { SalesReportComponent } from './features/reports/sales-report/sales-report';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
    { path: 'login', component: LoginComponent },
    { 
        path: 'dashboard', 
        component: DashboardComponent, 
        canActivate: [roleGuard(['OWNER'])] 
    },
    { 
        path: 'pos', 
        component: PosComponent,
        canActivate: [roleGuard(['OWNER', 'CASHIER'])] // Cualquiera logueado puede entrar (Cajero o Dueño)
    },
    { 
        path: 'team', 
        component: TeamComponent, 
        canActivate: [roleGuard(['OWNER', 'ADMIN'])] 
    },
    {
        path: 'hhrr',
        component: EmployeesComponent,
        canActivate: [roleGuard(['OWNER', 'HHRR'])]
    },
    { 
        path: 'reports/sales', 
        component: SalesReportComponent,
        canActivate: [roleGuard(['OWNER', 'ADMIN'])]
    },
    { 
        path: 'inventory/add', 
        component: ProductFormComponent,
        canActivate: [roleGuard(['OWNER', 'ADMIN'])] 
    },
    { path: '', redirectTo: '/login', pathMatch: 'full' },
];
