import { Injectable, inject } from "@angular/core";
import { HttpClient, HttpParams } from "@angular/common/http";
import { Observable } from "rxjs";

const API_URL = 'http://localhost:80/api';

@Injectable({ providedIn: 'root' })
export class ApiService {
    private http = inject(HttpClient);

    get<T>(path: string, params: Record<string, any> = {}): Observable<T> {
        let httpParams = new HttpParams();
        Object.keys(params).forEach(key => {
            if (params[key] !== null && params[key] !== undefined) {
                httpParams = httpParams.set(key, params[key]);
            }
        });
        return this.http.get<T>(`${API_URL}/${path}`, { params: httpParams });
    }
}