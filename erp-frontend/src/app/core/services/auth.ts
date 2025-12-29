import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap, of, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private apiUrl = `${environment.apiUrl}/auth`;

  // Signals para estado reactivo
  currentUser = signal<any>(null);
  isAuthenticated = signal<boolean>(!!localStorage.getItem('access_token'));

  login(credentials: any): Observable<AuthResponse> {  
    const formData = new FormData();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);

    return this.http.post<AuthResponse>(`${this.apiUrl}/login`, formData).pipe(
      tap(response => this.setSession(response))
    );
  }

  register(data: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/register`, data);
  }

  // Refresh Token
  refreshToken(): Observable<AuthResponse> {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
        // Si no hay refresh token, no podemos renovar. Logout forzado.
        this.logout();
        return throwError(() => new Error('No refresh token'));
    }

    return this.http.post<AuthResponse>(`${this.apiUrl}/refresh`, {
      refresh_token: refreshToken
    }).pipe(
        tap(response => this.setSession(response))
    );
  }

  private setSession(authResult: AuthResponse) {
    localStorage.setItem('access_token', authResult.access_token);
    // Solo guardamos refresh si viene en la respuesta (a veces solo viene access)
    if (authResult.refresh_token) {
        localStorage.setItem('refresh_token', authResult.refresh_token);
    }
    this.isAuthenticated.set(true);
  }

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.isAuthenticated.set(false);
    this.router.navigate(['/login']);
  }
}