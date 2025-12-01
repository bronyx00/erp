import { patchState, signalStore, withMethods, withState } from '@ngrx/signals';
import { inject } from '@angular/core';
import { ApiService } from '../../../core/api/api.service';
import { Invoice } from '../../../core/services/finance';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { pipe, switchMap, tap, catchError, of } from 'rxjs';

interface InvoiceState {
    invoices: Invoice[];
    isLoading: boolean;
    filter: string;
}

const initialState: InvoiceState = {
    invoices: [],
    isLoading: false,
    filter: 'ALL'
};

export const InvoiceStore = signalStore(
    { providedIn: 'root' },
    withState(initialState),
    withMethods((store, api = inject(ApiService)) => ({
        loadInvoices: rxMethod<void>(
            pipe(
                tap(() => patchState(store, { isLoading: true })),
                switchMap(() => {
                    // Pide las últimas 10 facturas para el dashboard
                    return api.get<any>('finance/invoices', { limit: 10 }).pipe(
                        tap((response) => {
                            console.log('Facturas cargadas:', response);
                            patchState(store, {
                                invoices: response.data,
                                isLoading: false
                            });
                        }),
                        catchError((err) => {
                            console.error('Error cargando facturas:', err);
                            patchState(store, { isLoading: false });
                            return of(null);
                        })
                    );
                })
            )
        )
    }))
);