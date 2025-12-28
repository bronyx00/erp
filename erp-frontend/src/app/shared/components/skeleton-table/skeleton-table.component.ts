import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-skeleton-table',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="w-full animate-pulse p-4">
        <div class="h-8 bg-slate-100 rounded mb-4 w-full"></div>
        
        @for (i of rowsArray; track i) {
            <div class="flex gap-4 py-3 border-b border-slate-50">
                <div class="h-4 bg-slate-200 rounded w-1/3"></div>
                <div class="h-4 bg-slate-200 rounded w-1/6"></div>
                <div class="h-4 bg-slate-200 rounded w-1/6"></div>
                <div class="h-4 bg-slate-200 rounded w-1/6"></div>
            </div>
        }
    </div>
  `
})
export class SkeletonTableComponent {
  @Input() rows: number = 5;
  get rowsArray() { return Array(this.rows).fill(0); }
}