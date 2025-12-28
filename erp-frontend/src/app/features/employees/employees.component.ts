import { Component, OnInit, inject, signal, computed, ViewChild } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs';

import { HhrrService, Employee } from '../../core/services/hhrr';
import { AccessControlComponent } from './components/access-control/access-control.component';
import { UserFormComponent } from './components/user-form/user-form.component';
import { EmployeeFormComponent } from './components/employee-form/employee-form.component';
import { EmployeeProfileComponent } from './components/employee-profile/employee-profile.component';
import { ScheduleManagerComponent } from './components/schedule-manager/schedule-manager.component';
import { PayrollHistoryComponent } from './components/payroll-history/payroll-history.component';
import { PayrollGeneratorComponent } from './components/payroll-generator/payroll-generator.component';
import { UsersService } from '../../core/services/users';


type Tab = 'EMPLOYEES' | 'PAYROLL' | 'ACCESS';
type DrawerMode = 'CREATE' | 'VIEW_PROFILE' | 'EDIT' | 'MANAGE_SCHEDULE' | 'CREATE_USER';

@Component({
    selector: 'app-employees',
    standalone: true,
    imports: [
        CommonModule, ReactiveFormsModule, CurrencyPipe, DatePipe, 
        EmployeeFormComponent, EmployeeProfileComponent, ScheduleManagerComponent,
        PayrollHistoryComponent, PayrollGeneratorComponent, AccessControlComponent,
        UserFormComponent
    ],
    templateUrl: './employees.component.html'
})
export class EmployeesComponent implements OnInit {
    private hhrrService = inject(HhrrService);
    private usersService = inject(UsersService)

    // Referencia para recargar la tabla de usuarios
    @ViewChild(AccessControlComponent) accessControl!: AccessControlComponent;

    // UI State
    activeTab = signal<Tab>('EMPLOYEES');
    searchControl = new FormControl('');
    searchTerm = signal('');
    viewMode = signal<'ACTIVE' | 'HISTORY'>('ACTIVE');
    totalSystemUsers = signal(0);

    // Data State
    employees = signal<Employee[]>([]);
    isLoading = signal(true);

    // Pagination State
    currentPage = signal(1);
    pageSize = signal(10);
    totalItems = signal(0);
    serverPayrollTotal = signal(0);

    // Drawer & Modals
    isDrawerOpen = signal(false);
    drawerMode = signal<DrawerMode>('CREATE');
    selectedEmployee = signal<Employee | null>(null);
    isPayrollWizardOpen = signal(false);

    stats = computed(() => {
        return { 
            usersWithAccess: this.totalSystemUsers(), 
            active: this.employees().filter(e => e.is_active).length,
            monthlyPayroll: this.serverPayrollTotal() 
        };
    });

    // Pagination Helper
    paginationState = computed(() => {
        const total = this.totalItems();
        const current = this.currentPage();
        const size = this.pageSize();
        const start = total === 0 ? 0 : (current - 1) * size + 1;
        const end = Math.min(current * size, total);
        const totalPages = Math.ceil(total / size);

        return { start, end, total, totalPages, hasNext: current < totalPages, hasPrev: current > 1 };
    });

    displayedEmployees = computed(() => {
        const all = this.employees();
        const mode = this.viewMode();
        
        return all.filter(emp => {
            if (mode === 'ACTIVE') return emp.is_active;
            if (mode === 'HISTORY') return !emp.is_active;
            return true;
        });
    });

    ngOnInit() {
        this.loadData();

        // Buscador Reactivo
        this.searchControl.valueChanges
            .pipe(debounceTime(400), distinctUntilChanged())
            .subscribe(val => {
                const term = val || '';
                this.searchTerm.set(term);

                // Si estamos en Empleados, recargamos la tabla
                if (this.activeTab() === 'EMPLOYEES') {
                    this.currentPage.set(1); // Reset a página 1 al buscar
                    this.loadData();
                }
            });
    }

    changeTab(tab: Tab) {
        this.activeTab.set(tab);
        this.searchTerm.set('');
        this.searchControl.setValue('', { emitEvent: false }); 

        if (tab === 'EMPLOYEES') {
            this.currentPage.set(1);
            this.loadData();
        }
    }

    loadData() {
        this.isLoading.set(true);

        this.hhrrService.getEmployees(
            this.currentPage(), 
            this.pageSize(), 
            this.searchTerm()
        ).subscribe({
            next: (response: any) => {
                const list = Array.isArray(response) ? response : (response.data || []);

                const meta = response.meta || {};
                const total = meta.total !== undefined ? meta.total : list.length;

                const payrollSum = meta.monthly_payroll !== undefined ? meta.monthly_payroll : 0;

                this.employees.set(list);
                this.totalItems.set(total);
                this.serverPayrollTotal.set(payrollSum); // Guardamos el valor

                this.isLoading.set(false);
            },
            error: () => {
                this.employees.set([]);
                this.isLoading.set(false);
            }
        });

        this.usersService.getUsers(1, 1).subscribe(res => {
            this.totalSystemUsers.set(res.meta.total)
        });
    }

    changePage(newPage: number) {
        if (newPage < 1 || newPage > this.paginationState().totalPages) return;
            this.currentPage.set(newPage);
            this.loadData();
    }

    // --- ACCIONES GENERALES ---

    openCreate() {
        this.selectedEmployee.set(null);
        this.drawerMode.set('CREATE');
        this.isDrawerOpen.set(true);
    }

    openScheduleManager() {
        this.selectedEmployee.set(null); 
        this.drawerMode.set('MANAGE_SCHEDULE');
        this.isDrawerOpen.set(true);
    }

    openPayrollWizard() {
        this.isPayrollWizardOpen.set(true);
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
        this.loadData(); 
        this.closeDrawer();
    }

    getInitials(first: string, last: string): string {
        return (first.charAt(0) + last.charAt(0)).toUpperCase();
    }

    openProfile(employee: Employee) {
        this.selectedEmployee.set(employee);
        this.drawerMode.set('VIEW_PROFILE');
        this.isDrawerOpen.set(true);
    }

    closePayrollWizard() {
        this.isPayrollWizardOpen.set(false);
        // Opcional: Recargar historial si terminó
    }

    // --- ACCIONES DE USUARIOS (NUEVO) ---

    openCreateUser() {
        this.selectedEmployee.set(null);
        this.drawerMode.set('CREATE_USER');
        this.isDrawerOpen.set(true);
    }

    handleUserCreated() {
        this.closeDrawer();
        // Si estamos en la tab de accesos, refrescamos la tabla
        if (this.activeTab() === 'ACCESS' && this.accessControl) {
            this.accessControl.loadUsers();
        }
    }

    deactivateEmployee(employee: Employee, event: Event) {
    // Evitamos que el click se propague y abra el perfil del empleado
    event.stopPropagation();

    const confirmMessage = `⚠️ PROCESO DE BAJA (DESPIDO/RENUNCIA)\n\n` +
        `Estás a punto de dar de baja a: ${employee.first_name} ${employee.last_name}\n\n` +
        `ACCIONES AUTOMÁTICAS:\n` +
        `1. Se marcará como INACTIVO en RRHH.\n` +
        `2. Se REVOCARÁ inmediatamente su acceso al sistema (Usuario eliminado).\n` +
        `3. Se moverá a la lista de "Histórico".\n\n` +
        `¿Confirmar baja?`;

    if (!confirm(confirmMessage)) return;

    this.isLoading.set(true);

    // Payload mágico que detona el trigger en el backend
    const payload = {
        status: 'Inactive', 
        is_active: false 
    };

    // Usamos 'any' en el payload parcial si tu interfaz es estricta, 
    // o Partial<Employee> si tu servicio lo soporta.
    this.hhrrService.updateEmployee(employee.id, payload as any).subscribe({
        next: () => {
            this.isLoading.set(false);
            alert(`✅ ${employee.first_name} ha sido dado de baja correctamente.`);
            this.loadData(); // Recarga la lista -> El empleado se moverá a "Histórico"
        },
        error: (err) => {
            console.error(err);
            this.isLoading.set(false);
            alert('❌ Error al procesar la baja. Intente nuevamente.');
        }
    });
  }
    
}