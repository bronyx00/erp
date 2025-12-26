import { Component, EventEmitter, Input, Output, OnInit, inject, signal } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HhrrService, Employee, SupervisorNote } from '../../../../core/services/hhrr';

type ProfileTab = 'INFO' | 'NOTES';

@Component({
  selector: 'app-employee-profile',
  standalone: true,
  imports: [CommonModule, CurrencyPipe, DatePipe, FormsModule],
  templateUrl: './employee-profile.component.html',
  host: {
    class: 'block h-full overflow-hidden'
  }
})
export class EmployeeProfileComponent implements OnInit {
  private hhrrService = inject(HhrrService);

  @Input({ required: true }) employee!: Employee;
  @Output() onClose = new EventEmitter<void>();
  @Output() onEdit = new EventEmitter<Employee>();

  // Estado de Pestañas
  activeTab = signal<ProfileTab>('INFO');

  // Estado de Notas
  notes = signal<SupervisorNote[]>([]);
  isLoadingNotes = signal(false);
  
  // Nueva Nota
  newNoteContent = signal('');
  isSavingNote = signal(false);

  ngOnInit() {
    this.loadNotes();
  }

  loadNotes() {
    this.isLoadingNotes.set(true);
    this.hhrrService.getEmployeeNotes(this.employee.id).subscribe({
      next: (res) => {
        this.notes.set(res.data);
        this.isLoadingNotes.set(false);
      },
      error: () => this.isLoadingNotes.set(false)
    });
  }

  addNote() {
    if (!this.newNoteContent().trim()) return;

    this.isSavingNote.set(true);
    const payload = {
      employee_id: this.employee.id,
      category: 'GENERAL',
      content: this.newNoteContent(),
      is_private: false
    };

    this.hhrrService.createNote(payload).subscribe({
      next: (note) => {
        // Agregamos la nota al inicio de la lista localmente
        this.notes.update(current => [note, ...current]);
        this.newNoteContent.set('');
        this.isSavingNote.set(false);
      },
      error: (err) => {
        console.error(err);
        alert('Error al guardar la nota');
        this.isSavingNote.set(false);
      }
    });
  }

  getInitials(): string {
    return (this.employee.first_name.charAt(0) + this.employee.last_name.charAt(0)).toUpperCase();
  }
}