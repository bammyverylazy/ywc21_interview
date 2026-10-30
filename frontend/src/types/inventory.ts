import type { Product } from "./product";
export interface InventoryItem { _id: string; product_id: string; lot_number?: string | null; quantity: number; expiry_date: string; created_at: string; updated_at: string; product?: Product; }
