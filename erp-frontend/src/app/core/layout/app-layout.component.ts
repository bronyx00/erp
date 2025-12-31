import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, RouterOutlet, NavigationEnd } from '@angular/router';
import { AuthService } from '../services/auth';
import { filter } from 'rxjs';

interface MenuItem {
  label: string;
  icon: string;
  route?: string;
  children?: MenuItem[];
  isOpen?: boolean; // Para controlar el sub-menú
}

@Component({
  selector: 'app-app-layout',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app-layout.component.html',
  styleUrls: ['./app-layout.component.scss'] 
})
export class AppLayoutComponent implements OnInit {
  private authService = inject(AuthService);
  private router = inject(Router);

  // Estado del Sidebar
  isSidebarCollapsed = signal(false);
  isMobileMenuOpen = signal(false);
  
  currentUser = this.authService.currentUser;
  
  // Título de la página actual 
  pageTitle = signal('Dashboard');

  // --- CONFIGURACIÓN DEL MENÚ ---
  menuItems = signal<MenuItem[]>([
    { 
      label: 'Dashboard', 
      icon: 'fas fa-chart-pie', 
      route: '/dashboard' 
    },
    { 
      label: 'Punto de Venta', 
      icon: 'fas fa-cash-register', 
      route: '/pos' 
    },
    { 
      label: 'Inventario', 
      icon: 'fas fa-boxes-stacked', 
      route: '/inventory' 
    },
    { 
      label: 'Clientes (CRM)', 
      icon: 'fas fa-users', 
      route: '/crm' 
    },
    { 
      label: 'Recursos Humanos', 
      icon: 'fas fa-user-tie', 
      children: [
        { label: 'Empleados', icon: 'fas fa-id-card', route: '/hhrr' },
        { label: 'Nómina', icon: 'fas fa-file-invoice-dollar', route: '/hhrr/payroll' },
        { label: 'Asistencia', icon: 'fas fa-clock', route: '/hhrr/attendance' }
      ]
    },
    { 
      label: 'Finanzas', 
      icon: 'fas fa-coins', 
      children: [
        { label: 'Facturas', icon: 'fas fa-file-invoice', route: '/finance/invoices' },
        { label: 'Cotizaciones', icon: 'fas fa-receipt', route: '/quotes' },
        { label: 'Cierres de Caja', icon: 'fas fa-wallet', route: '/finance/cash-close' }
      ]
    },
    { 
      label: 'Configuración', 
      icon: 'fas fa-cogs', 
      route: '/settings' 
    }
  ]);
  
  ngOnInit() {
    if (this.authService.isAuthenticated() && !this.currentUser()) {
        this.authService.me().subscribe({
            error: () => this.authService.logout() // Si falla (token invalido), logout
        });
    }
  }

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

  constructor() {
    // Detectar cambios de ruta para actualizar título o cerrar menú móvil
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe(() => {
      this.isMobileMenuOpen.set(false);
      this.updateTitle();
    });
  }

  toggleSidebar() {
    this.isSidebarCollapsed.update(v => !v);
  }

  toggleMobileMenu() {
    this.isMobileMenuOpen.update(v => !v);
  }

  toggleSubmenu(item: MenuItem) {
    if (!this.isSidebarCollapsed()) {
      item.isOpen = !item.isOpen;
    } else {
      // Si está colapsado y hacen click, expandimos para mostrar el submenú
      this.isSidebarCollapsed.set(false);
      item.isOpen = true;
    }
  }

  logout() {
    if(confirm('¿Cerrar sesión?')) {
      this.authService.logout();
    }
  }

  private updateTitle() {
    // Lógica simple para obtener título basado en la URL
    const url = this.router.url.split('/')[1];
    if (url) {
      this.pageTitle.set(url.charAt(0).toUpperCase() + url.slice(1));
    }
  }
}