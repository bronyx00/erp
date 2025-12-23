export type MeasurementUnit = 'UNIT' | 'KG' | 'METER' | 'LITER' | 'SERVICE';

export interface Product {
  id: number;
  sku: string;
  name: string;
  description: string | null;
  category: string;
  measurementUnit: MeasurementUnit; 
  price: number;
  stock: number;
  isActive: boolean;
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