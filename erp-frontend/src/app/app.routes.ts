import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login';
import { DashboardComponent } from './features/dashboard/dashboard';
import { PosComponent } from './features/pos/pos';
import { TeamComponent } from './features/team/team';
import { EmployeesComponent } from './features/employees/employees';
import { inject } from '@angular/core';
import { AuthService } from './core/services/auth';
import { Router } from '@angular/router';
import { ProductFormComponent } from './features/inventory/product-form/product-form';
import { SalesReportComponent } from './features/reports/sales-report/sales-report';

// Protección simple de la ruta
const authGuard = () => {
    const auth = inject(AuthService);
    const router = inject(Router);

    if (auth.currentUser()) {
        return true;
    }
    // Si no hay usuario, mandar al login
    return router.parseUrl('/login');
};

const adminGuard = () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const role = auth.currentUserRole();

    if (role === 'OWNER' || role === 'ADMIN') {
        return true;
    }
    alert('Acceso denegado: Se requiere nivel Administrativo');
    return false;
};

const hhrrGuard = () => {
    const auth = inject(AuthService);
    const role = auth.currentUserRole();
    // Solo Dueño o RRHH pueden entrar
    if (role === 'OWNER' || role === 'HHRR') return true;
    alert('Acceso denegado: Área restringida a RRHH');
    return false;
}

export const routes: Routes = [
    { path: 'login', component: LoginComponent },
    { 
        path: 'dashboard', 
        component: DashboardComponent, 
        canActivate: [authGuard] 
    },
    { 
        path: 'pos', 
        component: PosComponent,
        canActivate: [authGuard] // Cualquiera logueado puede entrar (Cajero o Dueño)
    },
    { 
        path: 'team', 
        component: TeamComponent, 
        canActivate: [authGuard, adminGuard] 
    },
    {
        path: 'hhrr',
        component: EmployeesComponent,
        canActivate: [authGuard, hhrrGuard]
    },
    { 
        path: 'reports/sales', 
        component: SalesReportComponent,
        canActivate: [authGuard, adminGuard]
    },
    { 
        path: 'inventory/add', 
        component: ProductFormComponent,
        canActivate: [authGuard, adminGuard] 
    },
    { path: '', redirectTo: '/login', pathMatch: 'full' },
];
