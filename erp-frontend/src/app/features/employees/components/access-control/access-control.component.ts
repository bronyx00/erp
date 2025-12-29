import { Component, OnInit, inject, signal, Input, computed, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UsersService, User } from '../../../../core/services/users';

@Component({
    selector: 'app-access-control',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './access-control.component.html' // Referencia al archivo externo
})
export class AccessControlComponent implements OnInit {
    private userService = inject(UsersService);

    @Output() onCreate = new EventEmitter<void>();
    

    private searchQuery = signal('');
    @Input() set searchTerm(value: string) {
        this.searchQuery.set(value);
        this.currentPage.set(1);
        this.loadUsers();
    }

    users = signal<User[]>([]);
    isLoading = signal(true);

    currentPage = signal(1);
    pageSize = signal(10);
    totalItems = signal(0);

    paginationState = computed(() => {
        const total = this.totalItems();
        const current = this.currentPage();
        const size = this.pageSize();
        const start = total === 0 ? 0 : (current - 1) * size + 1;
        const end = Math.min(current * size, total);
        return { start, end, total, hasNext: current * size < total, hasPrev: current > 1 };
    });

    ngOnInit() {
    this.loadUsers();
    }

    loadUsers() {
        this.isLoading.set(true);
        this.userService.getUsers(this.currentPage(), this.pageSize(), this.searchQuery()).subscribe({
            next: (res) => {
                this.users.set(res.data);
                this.totalItems.set(res.meta.total);
                this.isLoading.set(false);
            },
            error: () => {
                this.users.set([]);
                this.isLoading.set(false);
            }
        });
    }

    changePage(page: number) {
        if (page < 1) return;
            this.currentPage.set(page);
            this.loadUsers();
    }

    deleteUser(user: User) {
        if (!confirm(`Estás a punto de revocar el acceso al sistema para:\n${user.full_name || user.email}\n\nEl empleado seguirá existiendo en RRHH, pero ya no podrá iniciar sesión.\n¿Confirmar bloqueo?`)) {
        return;
        }

        this.isLoading.set(true);
        this.userService.deleteUser(user.id).subscribe({
            next: () => {
                alert('✅ Acceso revocado correctamente.\nEl usuario ha sido desactivado.');
                this.loadUsers(); // Recargamos la tabla
            },
            error: (err) => {
                console.error(err);
                alert('❌ Hubo un error al intentar eliminar el acceso.');
                this.isLoading.set(false);
            }
        });
    }

    getRoleBadgeClass(role: string): string {
        switch(role) {
            case 'ADMIN': return 'bg-purple-50 text-purple-700 border-purple-200';
            case 'OWNER': return 'bg-slate-800 text-white border-slate-900';
            case 'SALES_AGENT': return 'bg-blue-50 text-blue-700 border-blue-200';
            case 'SALES_SUPERVISOR': return 'bg-blue-100 text-blue-800 border-blue-300';
            case 'ACCOUNTANT': return 'bg-amber-50 text-amber-700 border-amber-200';
            case 'RRHH_MANAGER': return 'bg-rose-50 text-rose-700 border-rose-200';
            case 'PROJECT_MANAGER': return 'bg-cyan-50 text-cyan-700 border-cyan-200';
            case 'WAREHOUSE_CLERK': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
            case 'WAREHOUSE_SUPERVISOR': return 'bg-emerald-100 text-emerald-800 border-emerald-300';
            default: return 'bg-slate-50 text-slate-600 border-slate-200';
        }
    }
}