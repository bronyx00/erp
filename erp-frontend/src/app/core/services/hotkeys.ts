import { Injectable, OnDestroy } from '@angular/core';
import { EventManager } from '@angular/platform-browser';
import { Observable, Subject, fromEvent, Subscription } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class HotkeysService implements OnDestroy {
  // Usamos Subject para emitir eventos de teclas específicas
  private f1Subject = new Subject<void>();  // Bucar
  private f2Subject = new Subject<void>();  // Agregar cantidad
  private f4Subject = new Subject<void>();  // Cambiar Cliente
  private f5Subject = new Subject<void>();  // Cobrar
  private escSubject = new Subject<void>(); // Cancelar / Cerrar Modal

  // Exponemos como Observables
  f1$ = this.f1Subject.asObservable();
  f2$ = this.f2Subject.asObservable();
  f4$ = this.f4Subject.asObservable();
  f5$ = this.f5Subject.asObservable();
  esc$ = this.escSubject.asObservable();

  private keySubscription: Subscription;

  constructor(private eventManager: EventManager) {
    // Escuchamos globalmente en todo el documento
    this.keySubscription = fromEvent<KeyboardEvent>(document, 'keydown').subscribe((event) => {
      this.handleKeyboardEvent(event);
    })
  }

  ngOnDestroy() {
    if (this.keySubscription) {
      this.keySubscription.unsubscribe();
    }
  }

  private handleKeyboardEvent(event: KeyboardEvent) {
    // Ignorar si el usuario está escribiendo en un input
    const target = event.target as HTMLElement;
    if (target.tagName === 'INPUT' && event.key !== 'Escape' && event.key !== 'Enter') return;

    switch (event.key) {
      case 'F1':
        event.preventDefault(); // Evitar ayuda del navegador
        this.f1Subject.next();
        break;
      case 'F2':
        event.preventDefault();
        this.f2Subject.next();
        break;
      case 'F4':
        event.preventDefault();
        this.f4Subject.next();
        break;
      case 'F5':
        event.preventDefault(); // Evitar recargar página
        this.f5Subject.next();
        break;
      case 'Escape':
        event.preventDefault();
        this.escSubject.next();
        break;
    }
  }
}
