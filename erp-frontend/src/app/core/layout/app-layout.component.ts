import { Component, signal } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../services/auth';

@Component({
  selector: 'app-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="flex h-screen bg-slate-50 font-sans text-slate-900 overflow-hidden">
      
      <aside class="bg-slate-900 text-white flex flex-col transition-all duration-300 w-64">
        <div class="h-16 flex items-center px-6 border-b border-slate-800">
          <span class="font-bold text-xl tracking-tight">ERP Cloud</span>
        </div>

        <nav class="flex-1 py-6 px-3 space-y-1">
          <a routerLink="/dashboard" routerLinkActive="bg-blue-600 text-white" 
             class="flex items-center px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
             Dashboard
          </a>
          <a routerLink="/hhrr" 
             class="flex items-center px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
             Detalles de Empleados
          </a>
          <a routerLink="/hhrr/employees" 
             class="flex items-center px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
             Recursos Humanos
          </a>
          <a routerLink="/accounting" 
             class="flex items-center px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
             Contabilidad y Finanzas
          </a>
          <a routerLink="/accounting/books" 
             class="flex items-center px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
             Libros Contables
          </a>
          <a routerLink="/accounting/expenses" 
             class="flex items-center px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
              Gastos
          </a>
          <a routerLink="/crm" 
             class="flex items-center px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
             CRM
          </a>
          <a routerLink="/pos" 
             class="flex items-center px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
             Punto de Venta
          </a>
          <a routerLink="/inventory/products" 
             class="flex items-center px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
             Inventario
          </a>
          <a routerLink="/inventory/products/new" 
             class="flex items-center px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
             Crear Producto
          </a>
          <a routerLink="/reports/daily-sales" 
             class="flex items-center px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
             Cierre de Caja
          </a>
          </nav>

        <div class="p-4 border-t border-slate-800">
          <button (click)="logout()" class="text-sm text-slate-400 hover:text-white">Cerrar Sesión</button>
        </div>
      </aside>

      <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header class="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shadow-sm">
          <h2 class="text-lg font-medium text-slate-800">Bienvenido</h2>
          <div class="h-8 w-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-bold">
            U
          </div>
        </header>

        <main class="flex-1 overflow-auto p-8">
          <router-outlet></router-outlet>
        </main>
      </div>
    </div>
  `
})
export class AppLayoutComponent {
  constructor(private auth: AuthService) {}
  logout() { this.auth.logout(); }
}