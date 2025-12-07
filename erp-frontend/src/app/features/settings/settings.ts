import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SettingsService, CompanySettings } from '../../core/services/settings';
import { Title } from '@angular/platform-browser';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './settings.html',
})
export class Settings {
  private settingsService = inject(SettingsService);
  private titleService = inject(Title);

  activeTab: 'company' | 'fiscal' | 'invoice' = 'company';
  previewMode: 'TICKET' | 'A4' = 'A4'; // Modo de previsualización de factura

  settings = signal<CompanySettings>({} as CompanySettings);
  isLoading = signal(true);
  isSaving = signal(false);

  // Datos Dummy para la previsualización de la factura
  mockInvoiceItems = [
    { qty: 1, desc: 'Laptop Pro 15"', price: 1200.00, total: 1200.00 },
    { qty: 2, desc: 'Mouse Inalámbrico', price: 25.00, total: 50.00 },
    { qty: 1, desc: 'Soporte de Aluminio', price: 45.00, total: 45.00 },
  ];

  ngOnInit() {
    this.titleService.setTitle('ERP - Configuración');
    this.loadSettings();
  }

  loadSettings() {
    this.settingsService.getSettings().subscribe(data => {
      this.settings.set(data);
      this.isLoading.set(false);
    });
  }

  save() {
    this.isSaving.set(true);
    this.settingsService.updateSettings(this.settings()).subscribe(() => {
      setTimeout(() => { // Simular delay de red
        this.isSaving.set(false);
        alert('Configuración guardada exitosamente');
      }, 800);
    });
  }

  // Cálculos para la previsualización
  get subtotalPreview() {
    return this.mockInvoiceItems.reduce((acc, item) => acc + item.total, 0);
  }

  get taxPreview() {
    if (!this.settings().tax_active) return 0;
    return this.subtotalPreview * (this.settings().tax_rate / 100);
  }

  get totalPreview() {
    return this.subtotalPreview + this.taxPreview;
  }
  
  onLogoSelected(event: any) {
      const file = event.target.files[0];
      if (file) {
          const reader = new FileReader();
          reader.onload = (e: any) => {
              this.settings.update(s => ({...s, logoUrl: e.target.result}));
          };
          reader.readAsDataURL(file);
      }
  }
}
