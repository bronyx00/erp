import { Component, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../services/auth';

// 1. Definimos la interfaz estricta para tu menú
interface MenuItem {
  label: string;
  icon: string;       // Clase de FontAwesome (ej: 'fas fa-home')
  route?: string;     // Opcional si tiene hijos
  children?: MenuItem[];
  isOpen?: boolean;   // Estado para el acordeón
}

@Component({
  selector: 'app-layout',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app-layout.component.html',
  styles: [`
    /* Scrollbar personalizado para que combine con el diseño */
    .custom-scrollbar::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
      background: transparent;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background-color: #cbd5e1;
      border-radius: 20px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
      background-color: #94a3b8;
    }
  `]
})
export class AppLayoutComponent {
  private authService = inject(AuthService);
  
  // -- STATE SIGNALS --
  isSidebarCollapsed = signal(false);
  isMobileMenuOpen = signal(false);
  
  // Mock User Data (Reemplazar con AuthService.user())
  currentUser = this.authService.currentUser;

  // -- MENU CONFIGURATION (Dynamic & Type Safe) --
  menuItems = signal<MenuItem[]>([
    { 
      label: 'Dashboard', 
      route: '/dashboard', 
      icon: 'fas fa-chart-pie' 
    },
    
    // SECCIÓN CONTABILIDAD (Anidada)
    { 
      label: 'Contabilidad', 
      icon: 'fas fa-calculator', // Icono FontAwesome
      isOpen: false, // Cerrado por defecto
      children: [
        { label: 'Plan de Cuentas', route: '/accounting/chart-of-accounts', icon: '' },
        { label: 'Libro Diario', route: '/accounting/journal', icon: '' },
        { label: 'Reportes', route: '/accounting/reports', icon: '' },
      ]
    },

    // SECCIÓN FINANZAS (Anidada)
    {
      label: 'Finanzas',
      icon: 'fas fa-file-invoice-dollar',
      isOpen: false,
      children: [
        { label: 'Facturas', route: '/finance/invoices', icon: '' },
        { label: 'Cotizaciones', route: '/finance/quotes', icon: '' },
      ]
    },

    { label: 'Inventario', route: '/inventory', icon: 'fas fa-boxes' },
    { label: 'CRM Clientes', route: '/crm', icon: 'fas fa-users' },
    { label: 'RRHH', route: '/hr', icon: 'fas fa-id-card' },
    { label: 'Punto de Venta', route: '/pos', icon: 'fas fa-cash-register' },
    { label: 'Configuración', route: '/settings', icon: 'fas fa-cog' },
  ]);

  getRoleLabel(role: string | undefined): string {
      const roles: any = {
          'OWNER': 'Dueño',
          'ADMIN': 'Administrador',
          'SALES_AGENT': 'Vendedor',
          'RRHH_MANAGER': 'Gerente RRHH',
          'WAREHOUSE_SUPERVISOR': 'Supervisor Almacén'
      };
      return role ? (roles[role] || role) : 'Usuario';
  }



  ngOnInit() {
    if (this.authService.isAuthenticated() && !this.currentUser()) {
        this.authService.me().subscribe({
            error: () => this.authService.logout() // Si falla (token invalido), logout
        });
    }
  }

  // -- ACTIONS --

  toggleSidebar() {
    this.isSidebarCollapsed.update(v => !v);
  }

  toggleMobileMenu() {
    this.isMobileMenuOpen.update(v => !v);
  }

  // Lógica para el Acordeón del Menú
  toggleSubmenu(label: string) {
    // Si la sidebar está colapsada, al abrir un submenú deberíamos expandirla para UX
    if (this.isSidebarCollapsed()) {
      this.isSidebarCollapsed.set(false);
    }

    this.menuItems.update(items => 
      items.map(item => {
        if (item.label === label) {
          return { ...item, isOpen: !item.isOpen };
        }
        // Opcional: Cerrar los otros menús al abrir uno (Accordion Effect)
        // return { ...item, isOpen: false }; 
        return item;
      })
    );
  }

  logout() {
    if(confirm('¿Cerrar sesión?')) {
      this.authService.logout();
    }
  }
}