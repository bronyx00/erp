import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth';

/**
 * Fábrica de Guards: Permite definir roles permitidos al configurar la ruta.
 * Uso en routes: canActivate: [roleGuard(['OWNER', 'ADMIN'])]
 */
export const roleGuard = (allowedRoles: string[]): CanActivateFn => {
  return (route, state) => {
    const auth = inject(AuthService);
    const router = inject(Router);
    
    // 1. Verificar Autenticación
    if (!auth.currentUser()) {
      return router.createUrlTree(['/login']);
    }

    // 2. Verificar Rol
    const userRole = auth.currentUser(); // Ej: 'CASHIER'
    
    if (allowedRoles.includes(userRole)) {
      return true; // Acceso concedido
    }

    // 3. Acceso Denegado
    console.warn(`⛔ Acceso denegado. Requerido: ${allowedRoles}, Actual: ${userRole}`);
    alert('No tienes permisos para acceder a esta sección.');
    
    // Redirigir a un lugar seguro (Dashboard o POS según el rol)
    return router.createUrlTree(['/dashboard']);
  };
};