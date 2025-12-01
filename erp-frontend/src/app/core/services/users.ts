import { Injectable , inject} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface User {
  id?: number;
  email: string;
  role: string;
  is_active: boolean;
  password?: string;
}

@Injectable({
  providedIn: 'root',
})
export class UsersService {
  private http = inject(HttpClient);
  private readonly API_URL = 'http://localhost:80/api/auth';

  // Obtener lista de empleados
  getEmployees(): Observable<User[]> {
    return this.http.get<User[]>(`${this.API_URL}/users`);
  }

  // Crear nuevo empleado
  createEmployee(user: User): Observable<User> {
    return this.http.post<User>(`${this.API_URL}/users`, user);
  }
}
