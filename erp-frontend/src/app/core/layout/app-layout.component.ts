import { Component, signal } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-layout',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="flex h-screen bg-slate-50 font-sans text-slate-900">
      
      <aside 
        class="bg-slate-900 text-white flex flex-col transition-all duration-300 ease-in-out overflow-hidden"
        [class.w-64]="!isCollapsed()"
        [class.w-20]="isCollapsed()">
        
        <div class="h-16 flex items-center px-6 border-b border-slate-800/50">
          <div class="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-lg shrink-0">
            E
          </div>
          @if (!isCollapsed()) {
            <span class="ml-3 font-semibold tracking-tight text-lg animate-fade-in">ERP Cloud</span>
          }
        </div>

        <nav class="flex-1 py-6 px-3 space-y-1">
          @for (item of navItems; track item.label) {
            <a [routerLink]="item.route" 
               routerLinkActive="bg-blue-600 text-white shadow-lg shadow-blue-900/50"
               class="flex items-center px-3 py-2.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all group">
              
              <span class="shrink-0" [innerHTML]="item.icon"></span>
              
              @if (!isCollapsed()) {
                <span class="ml-3 font-medium text-sm whitespace-nowrap animate-fade-in">{{ item.label }}</span>
              }
              
              @if (isCollapsed()) {
                <div class="absolute left-16 bg-slate-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                  {{ item.label }}
                </div>
              }
            </a>
          }
        </nav>

        <div class="p-4 border-t border-slate-800/50">
          <button (click)="toggleSidebar()" class="w-full flex items-center justify-center p-2 rounded-lg hover:bg-slate-800 text-slate-400">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7"></path></svg>
          </button>
        </div>
      </aside>

      <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
        
        <header class="h-16 bg-white border-b border-slate-200 flex justify-between items-center px-6 shadow-sm z-10">
          <div class="flex items-center text-sm text-slate-500">
            <span class="text-slate-400">Organización</span>
            <span class="mx-2">/</span>
            <span class="font-medium text-slate-800">Dashboard</span>
          </div>

          <div class="flex items-center gap-4">
            <div class="relative">
              <input type="text" placeholder="Comando (Ctrl+K)" 
                     class="bg-slate-50 border border-slate-200 rounded-md py-1.5 pl-3 pr-8 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 w-64 transition-all">
              <span class="absolute right-2 top-1.5 text-xs text-slate-400 border border-slate-200 rounded px-1">⌘K</span>
            </div>
            
            <div class="h-8 w-8 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-bold border border-blue-200 cursor-pointer">
              JS
            </div>
          </div>
        </header>

        <main class="flex-1 overflow-auto p-0 scroll-smooth">
          <router-outlet />
        </main>
      </div>
    </div>
  `,
  styles: [`
    .animate-fade-in { animation: fadeIn 0.2s ease-in; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  `]
})
export class AppLayoutComponent {
  isCollapsed = signal(false);

  navItems = [
    { label: 'Dashboard', route: '/dashboard', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"></path></svg>' },
    { label: 'Facturación', route: '/invoices', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>' },
    { label: 'Inventario', route: '/inventory', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path></svg>' },
    { label: 'Equipo', route: '/team', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>' },
  ];

  toggleSidebar() {
    this.isCollapsed.update(v => !v);
  }
}