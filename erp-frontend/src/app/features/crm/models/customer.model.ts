// Definimos la estructura de la paginación que viene de Python
export interface ApiMetadata {
  total: number;
  page: number;
  limit: number;
  totalPages: number; // Mapeado de total_pages
}

export interface PaginatedResult<T> {
  data: T[];
  meta: ApiMetadata;
}

// Interfaz pura de Frontend
export interface Customer {
  id: number;
  name: string;
  email: string | null;
  taxId: string | null; // Mapeado de tax_id
  phone: string | null;
  address: string | null;
  isActive: boolean;    // Mapeado de is_active
  createdAt: string;    // Mapeado de created_at
  // Campos calculados para UI 
  avatarInitials?: string;
}

// Payload para crear/editar (lo que enviaremos al backend)
export interface CustomerPayload {
  name: string;
  email?: string;
  tax_id?: string; // Al enviar, convertimos a snake_case para Python
  phone?: string;
  address?: string;
}