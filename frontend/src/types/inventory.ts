import type { Product } from "./product";
export type InventoryProductSummary = Pick<Product, "_id" | "brand_name" | "generic_name" | "registration_no" | "manufacturer">;
export interface InventoryItem { _id: string; product_id: string; lot_number?: string | null; quantity: number; expiry_date?: string | null; is_demo?: boolean; created_at: string; updated_at: string; product?: InventoryProductSummary; }
