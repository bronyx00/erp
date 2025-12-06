import { Component, OnInit, inject } from '@angular/core';
import { CommonModule, DatePipe, CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CrmService, Customer } from '../../../core/services/crm'; // Asegúrate de importar tu servicio y modelo
import { Title } from '@angular/platform-browser';

@Component({
  selector: 'app-client-management',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe, CurrencyPipe],
  templateUrl: './client-management.html',
  styleUrl: './client-management.scss',
})
export class ClientManagementComponent implements OnInit {
  private crmService = inject(CrmService);
  private titleService = inject(Title);

  // Data
  clients: Customer[] = [];
  selectedClient: Customer | null = null;
  
  // UI State
  isLoading = false;
  isModalOpen = false;
  isDetailPanelOpen = false;
  
  // Form Data (para el formulario modal)
  clientForm: Partial<Customer> = {}; 

  ngOnInit(): void {
    this.titleService.setTitle('ERP - Gestión de Clientes (CRM)');
    this.loadClients();
  }

  // Carga la lista de clientes
  loadClients(): void {
    this.isLoading = true;
    this.crmService.getCustomers().subscribe({
      next: (data) => {
        this.clients = data;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error al cargar clientes:', err);
        this.isLoading = false;
        // Aquí podrías mostrar una notificación de error al usuario
      }
    });
  }

  // --- Funciones de Detalle y CRM ---

  // Muestra el detalle del cliente en el panel lateral
  showClientDetails(client: Customer): void {
    this.selectedClient = client;
    this.isDetailPanelOpen = true;
    // Opcional: Podrías cargar datos más detallados del historial aquí si no vienen en la lista inicial
  }

  closeDetailPanel(): void {
    this.isDetailPanelOpen = false;
    this.selectedClient = null;
  }

  // Abre el modal para crear un cliente nuevo
  openCreateModal(): void {
    this.selectedClient = null;
    this.clientForm = {};
    this.isModalOpen = true;
  }

  // Abre el modal para editar un cliente existente
  openEditModal(client: Customer): void {
    this.selectedClient = client;
    this.clientForm = { ...client }; // Clonar los datos para el formulario
    this.isModalOpen = true;
  }

  // Cierra el modal
  closeModal(): void {
    this.isModalOpen = false;
    this.clientForm = {};
  }
  
  // --- Botones de Acción Rápida ---
  
  callClient(phone: string): void {
    // Abrir el cliente de teléfono predeterminado (ej. en desktop)
    window.open(`tel:${phone}`, '_self');
  }

  emailClient(email: string): void {
    // Abrir el cliente de correo predeterminado
    window.open(`mailto:${email}`, '_self');
  }

  whatsappClient(phone: string): void {
    // Abrir WhatsApp Web/App. Se recomienda sanitizar el número primero.
    const sanitizedPhone = phone.replace(/[^0-9]/g, ''); 
    window.open(`https://wa.me/${sanitizedPhone}`, '_blank');
  }

  // Guarda o actualiza el cliente
  saveClient(): void {
    if (this.selectedClient) {
      // Editar
      //this.crmService.updateClient(this.selectedClient.id, this.clientForm as Client).subscribe(() => {
        //this.loadClients();
        //this.closeModal();
      //});
    } else {
      // Crear
      this.crmService.createCustomer(this.clientForm as Customer).subscribe(() => {
        this.loadClients();
        this.closeModal();
      });
    }
  }

  // Elimina un cliente
  deleteClient(id: number): void {
    //if (confirm('¿Está seguro de que desea eliminar este cliente?')) {
      //this.crmService.deleteClient(id).subscribe(() => {
        //this.loadClients();
        // Mostrar notificación de éxito
      //});
    //}
  }
}