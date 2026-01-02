import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { 
  Account, 
  AccountCreate,
  AccountUpdate,
  LedgerEntryCreate, 
  LedgerEntryResponse, 
  EntryTemplate, 
  ApplyTemplateRequest 
} from '../models/accounting.models';

@Injectable({ providedIn: 'root' })
export class AccountingService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/accounting`;

  // --- CUENTAS ---
  getAccounts(transactionalOnly = false): Observable<Account[]> {
    let params = new HttpParams();
    if (transactionalOnly) {
      params = params.set('transactional', 'true');
    }
    return this.http.get<Account[]>(`${this.apiUrl}/accounts`, { params });
  }

  createAccount(acc: AccountCreate): Observable<Account> {
    return this.http.post<Account>(`${this.apiUrl}/accounts`, acc);
  }

  updateAccount(id: number, acc: AccountUpdate): Observable<Account> {
    return this.http.put<Account>(`${this.apiUrl}/accounts/${id}`, acc);
  }

  // --- ASIENTOS MANUALES ---
  createEntry(entry: LedgerEntryCreate): Observable<LedgerEntryResponse> {
    return this.http.post<LedgerEntryResponse>(`${this.apiUrl}/entries`, entry);
  }

  // --- PLANTILLAS (SMART ENGINE) ---
  getTemplates(): Observable<EntryTemplate[]> {
    return this.http.get<EntryTemplate[]>(`${this.apiUrl}/templates`);
  }

  previewTemplate(request: ApplyTemplateRequest): Observable<LedgerEntryCreate> {
    return this.http.post<LedgerEntryCreate>(`${this.apiUrl}/templates/preview`, request);
  }

  /**
   * Dispara la carga automática del PUC Venezuela.
   * @param sector - 'commerce', 'services', 'industry', 'agriculture'
   */
  seedDefaultPuc(sector: string): Observable<{ message: string }> {
    // Enviamos el objeto JSON { sector: "..." }
    return this.http.post<{ message: string }>(`${this.apiUrl}/accounts/seed-puc-ve`, { sector });
  }
}