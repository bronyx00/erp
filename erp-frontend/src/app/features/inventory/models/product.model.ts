export type MeasurementUnit = 'UNIT' | 'KG' | 'METER' | 'LITER' | 'SERVICE';

export interface Product {
    id: number;
    sku: string;
    name: string;
    description: string | null;
    category: string;
    measurement_unit: MeasurementUnit; 
    price: number;
    stock: number;
    is_active: boolean;
    tenant_id: number;
}

export interface ProductPayload {
    sku: string;
    name: string;
    description?: string;
    category?: string;
    measurement_unit: MeasurementUnit;
    price: number;
    stock: number;
}

export interface InventoryMetadata {
    total: number;
    page: number;
    limit: number;
    totalPages: number;
}

export interface PaginatedProductResult {
    data: Product[];
    meta: InventoryMetadata;
}