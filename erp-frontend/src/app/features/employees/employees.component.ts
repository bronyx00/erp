import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs';

import { HhrrService, Employee } from '../../core/services/hhrr';
import { EmployeeFormComponent } from './components/employee-form/employee-form.component';
import { EmployeeProfileComponent } from './components/employee-profile/employee-profile.component';
import { ScheduleManagerComponent } from './components/schedule-manager/schedule-manager.component';

type Tab = 'EMPLOYEES' | 'PAYROLL' | 'ACCESS';
type DrawerMode = 'CREATE' | 'VIEW_PROFILE' | 'EDIT' | 'MANAGE_SCHEDULE';

@Component({
  selector: 'app-employees',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, CurrencyPipe, DatePipe, EmployeeFormComponent, EmployeeProfileComponent, ScheduleManagerComponent],
  templateUrl: './employees.component.html'
})
export class EmployeesComponent implements OnInit {
  private hhrrService = inject(HhrrService);

  activeTab = signal<Tab>('EMPLOYEES');
  employees = signal<Employee[]>([]);
  isLoading = signal(true);

  searchControl = new FormControl('');
  searchTerm = signal('');

  // Drawer
  isDrawerOpen = signal(false);
  drawerMode = signal<DrawerMode>('CREATE');
  selectedEmployee = signal<Employee | null>(null);

  filteredEmployees = computed(() => {
    const term = this.searchTerm().toLowerCase();
    return this.employees().filter(e => 
      e.first_name.toLowerCase().includes(term) || 
      e.last_name.toLowerCase().includes(term) ||
      e.identification.includes(term) ||
      e.position.toLowerCase().includes(term)
    );
  });

  stats = computed(() => {
    const all = this.employees();
    const active = all.filter(e => e.is_active).length;
    const payroll = all.filter(e => e.is_active).reduce((acc, curr) => acc + parseFloat(curr.salary as string || '0'), 0);
    return { total: all.length, active, monthlyPayroll: payroll };
  });

  ngOnInit() {
    this.loadData();
    this.searchControl.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged())
      .subscribe(val => this.searchTerm.set(val || ''));
  }

  loadData() {
    this.isLoading.set(true);
    this.hhrrService.getEmployees().subscribe({
      next: (response: any) => {
        const list = Array.isArray(response) ? response : (response.data || []);
        this.employees.set(list);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false)
    });
  }

  // ACCIONES

  openProfile(employee: Employee) {
    this.selectedEmployee.set(employee);
    this.drawerMode.set('VIEW_PROFILE');
    this.isDrawerOpen.set(true);
  }

  openCreate() {
    this.selectedEmployee.set(null);
    this.drawerMode.set('CREATE');
    this.isDrawerOpen.set(true);
  }

  openScheduleManager() {
    this.selectedEmployee.set(null); // No necesitamos empleado seleccionado
    this.drawerMode.set('MANAGE_SCHEDULE');
    this.isDrawerOpen.set(true);
  }

  switchToEdit(employee: Employee) {
    this.selectedEmployee.set(employee);
    this.drawerMode.set('EDIT');
  }

  closeDrawer() {
    this.isDrawerOpen.set(false);
    this.selectedEmployee.set(null);
  }

  handleSave(employee: Employee) {
    this.loadData(); // Refrescar lista completa
    this.closeDrawer();
  }

  getInitials(first: string, last: string): string {
    return (first.charAt(0) + last.charAt(0)).toUpperCase();
  }
}