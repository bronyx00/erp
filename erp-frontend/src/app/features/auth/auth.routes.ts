import { Routes } from '@angular/router';

export const AUTH_ROUTES: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./login/login').then(m => m.LoginComponent),
    title: 'Iniciar Sesión'
  },
  {
    path: 'register',
    loadComponent: () => import('./register/register.component').then(m => m.RegisterComponent),
    title: 'Registrar cuenta'
  }
];