import { Component, OnInit, inject, signal, Input, computed, Output, EventEmitter } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { UsersService, User } from '../../../../core/services/users';

@Component({
  selector: 'app-access-control',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './access-control.component.html'
})
export class AccessControlComponent implements OnInit {
  private userService = inject(UsersService);

  @Output() onCreate = new EventEmitter<void>();

  // --- INPUT BUSCADOR REACTIVO ---
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
}