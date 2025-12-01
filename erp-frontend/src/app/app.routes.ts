import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login';
import { AppLayoutComponent } from './core/layout/app-layout.component';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  {
    path: '',
    component: AppLayoutComponent, // El Layout envuelve al dashboard
    canActivate: [roleGuard(['OWNER', 'ADMIN'])],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { 
        path: 'dashboard', 
        loadComponent: () => import('./features/dashboard/dashboard').then(m => m.DashboardComponent) 
      },
      // Aquí irán tus otras rutas hijas
    ]
  },
  { path: '**', redirectTo: 'login' }
];