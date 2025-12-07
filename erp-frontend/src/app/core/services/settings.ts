import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';

export type TaxType = 'EXCLUSIVE' | 'INCLUSIVE';
export type InvoiceFormat = 'TICKET' | 'FULL_PAGE';

export interface CompanySettings {
  // Datos inmutables
  legal_name: string;         // Razón Social
  tax_id: string;             // RIF

  // Datos Editables
  commercial_name: string;    // Nombre comercial
  address: string;
  phone: string;
  email: string;
  logo_url: string | null;
  category: string;

  // Fiscal
  tax_active: boolean;
  tax_rate: number;
  tax_type: TaxType;
  currency: string;

  // Personalización Factura
  invoice_notes: string;      // Pie de página default
  invoice_color: string;      // Color de acento (Hex)
}

const MOCK_SETTINGS: CompanySettings = {
  legal_name: 'INVERSIONES EL ÉXITO C.A.',
  tax_id: 'J-12345678-9',
  commercial_name: 'TechStore Venezuela',
  address: 'Av. Principal de Las Mercedes, Caracas',
  phone: '+58 412 555 5555',
  email: 'contacto@techstore.com',
  logo_url: 'https://via.placeholder.com/150', // Placeholder
  category: 'Retail / Tecnología',
  
  tax_active: true,
  tax_rate: 16,
  tax_type: 'EXCLUSIVE', // El precio base NO tiene IVA
  currency: 'USD',

  invoice_notes: 'Gracias por su compra. Conserve esta factura para reclamos de garantía (30 días).',
  invoice_color: '#4f46e5' // Indigo-600
};

@Injectable({
  providedIn: 'root',
})
export class SettingsService {
  getSettings(): Observable<CompanySettings> {
    return of(MOCK_SETTINGS);
  }

  updateSettings(settings: CompanySettings): Observable<CompanySettings> {
    console.log('Guardando configuración:', settings);
    return of(settings);
  }
}
