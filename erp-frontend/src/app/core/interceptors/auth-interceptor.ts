import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const token = authService.getToken();

  // Lista de URLs que NO necesitan token (Login y Registro)
  const excludedUrls = ['/api/auth/login', '/api/auth/register'];

  // Si la perición va a una URL exluida, pasarla sin tocar
  const isExcluded = excludedUrls.some(url => req.url.includes(url));

  if (token && !isExcluded) {
    // CLONAR la petición y agregarle el header Authorization
    const clonedReq = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
    return next(clonedReq);
  }

  return next(req);
};
