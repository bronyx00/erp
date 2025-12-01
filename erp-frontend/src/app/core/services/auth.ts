import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, tap } from 'rxjs/operators';
import { jwtDecode } from 'jwt-decode';

// Define la interfaz de la respuesta del Login
interface TokenResponse {
  access_token: string;
  token_type: string;
}

interface UserDecoded {
  sub: string; // email
  role: string;
  tenant_id: number;
  exp: number; // expiración
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  // URL de nuestra API Gateway (Traefik)
  private readonly API_URL = 'http://localhost:80/api/auth';
  private readonly TOKEN_KEY = 'erp_token';

  // Signal para saber si el usuario está logueado
  currentUser = signal<string | null>(null);
  currentUserRole = signal<string>('');

  constructor(private http: HttpClient) {
    // Al iniciar, verificamos si hay un token guardado
    this.loadToken();
  }

  login(email: string, password: string) {
    // En FastAPI OAuth2, los datos se envían como Form Data, no JSON
    const formData = new FormData();
    formData.append('username', email); // FastAPI espera 'username' aunque sea un email
    formData.append('password', password);

    return this.http.post<TokenResponse>(`${this.API_URL}/login`, formData).pipe(
      tap(response => this.saveToken(response.access_token))
    );
  }

  logout() {
    localStorage.removeItem(this.TOKEN_KEY);
    this.currentUser.set(null);
  }

  private saveToken(token: string) {
    localStorage.setItem(this.TOKEN_KEY, token);
    this.loadToken();
  }

  private loadToken() {
    const token = localStorage.getItem(this.TOKEN_KEY);
    if (token) {
      try {
        const decoded = jwtDecode<UserDecoded>(token);
        // Verificar si expiró 
        const isExpired = decoded.exp * 1000 < Date.now();

        if (!isExpired) {
          this.currentUser.set(decoded.sub);
          this.currentUserRole.set(decoded.role)
        } else {
          this.logout();
        }
      } catch (e) {
        this.logout();
      }
    }
  }

  // Helper para verificar permisos
  hasRole(allowedRoles: string[]): boolean {
    return allowedRoles.includes(this.currentUserRole())
  }

  // Login auxiliar apra el Model de Supervisor (NO guardar en localStorage)
  supervisorLogin(email: string, password: string) {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    return this.http.post<TokenResponse>(`${this.API_URL}/login`, formData);
  }

  // Método para obtener el token crudo
  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }
}

