import { Component, OnInit, inject, signal, ElementRef, ViewChild, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs';
import { CrmService } from '../services/crm.service';
import { Customer, ApiMetadata } from '../models/customer.model';
import { ClientFormComponent } from '../client-form/client-form.component';

@Component({
  selector: 'app-client-list',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, ClientFormComponent],
  templateUrl: './client-list.component.html',
  styleUrls: ['./client-list.component.scss']
})
export class ClientListComponent implements OnInit {
  private crmService = inject(CrmService);

  // --- SIGNALS STATE ---
  customers = signal<Customer[]>([]);
  meta = signal<ApiMetadata>({ total: 0, page: 1, limit: 10, totalPages: 0 });
  isLoading = this.crmService.isLoading;
  
  // UI State
  isDrawerOpen = signal(false);
  selectedCustomer = signal<Customer | null>(null);
  
  // Popover State 
  // Guardamos el ID del cliente que tiene el menú abierto
  activeMenuId = signal<number | null>(null);

  searchControl = new FormControl('');

  ngOnInit() {
    this.loadData();
    this.setupSearch();
  }

  // Cierra el menú si haces clic fuera
  @HostListener('document:click', ['$event'])
  onClickOutside(event: Event) {
    const target = event.target as HTMLElement;
    // Si el clic no fue en un botón de acción, cerramos el menú
    if (!target.closest('.action-trigger')) {
      this.activeMenuId.set(null);
    }
  }

  loadData(page: number = 1) {
    const searchTerm = this.searchControl.value || '';
    this.crmService.getCustomers(page, 10, searchTerm).subscribe({
      next: (res) => {
        this.customers.set(res.data);
        this.meta.set(res.meta);
        this.activeMenuId.set(null); // Cerrar menús al recargar
      },
      error: (err) => console.error('Error', err)
    });
  }

  setupSearch() {
    this.searchControl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged()
    ).subscribe(() => this.loadData(1));
  }

  // --- ACCIONES DE MENU (BURBUJA) ---

  toggleMenu(event: Event, customerId: number) {
    event.stopPropagation(); // Evita que el HostListener lo cierre inmediatamente
    event.preventDefault();  // Evita comportamientos extraños de botones

    if (this.activeMenuId() === customerId) {
      this.activeMenuId.set(null);
    } else {
      this.activeMenuId.set(customerId);
    }
  }

  contactWhatsApp(phone: string | null) {
    if (!phone) return;
    const sanitized = phone.replace(/[^0-9]/g, '');
    window.open(`https://wa.me/${sanitized}`, '_blank');
    this.activeMenuId.set(null);
  }

  contactEmail(email: string | null) {
    if (!email) return;
    window.open(`mailto:${email}`, '_self');
    this.activeMenuId.set(null);
  }

  // --- CRUD & EXPORT ---

  openCreate() {
    this.selectedCustomer.set(null);
    this.isDrawerOpen.set(true);
    this.activeMenuId.set(null);
  }

  openEdit(customer: Customer) {
    this.selectedCustomer.set(customer);
    this.isDrawerOpen.set(true);
    this.activeMenuId.set(null);
  }

  closeDrawer() {
    this.isDrawerOpen.set(false);
  }

  // Exportación "Client-Side" rápida (formato CSV)
  exportData() {
    const data = this.customers();
    if (data.length === 0) return;

    const headers = ['ID', 'Nombre', 'Email', 'Teléfono', 'RIF', 'Dirección'];
    const rows = data.map(c => [
      c.id, 
      `"${c.name}"`, // Comillas para evitar romper CSV con comas en nombres
      c.email || '', 
      c.phone || '', 
      c.taxId || '', 
      `"${c.address || ''}"`
    ]);

    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    // Crear link temporal y descargar
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `clientes_export_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  onFormSaved() {
    this.closeDrawer();
    this.loadData(this.meta().page); // Recargar página actual para ver cambios
    // Opcional: Mostrar un Toast de éxito aquí
  }

  onPageChange(newPage: number) {
    if (newPage >= 1 && newPage <= this.meta().totalPages) {
      this.loadData(newPage);
    }
  }
}