// PROVISIONAL: derived from README §6; response shapes not yet confirmed with backend.
export interface Product {
  _id: string;
  brand_name: string;
  generic_name?: string | null;
  registration_no?: string | null;
  manufacturer?: string | null;
  strength?: string | null;
  dosage_form?: string | null;
  data_origin?: "manual" | "demo" | "verified_source";
  created_at: string;
  updated_at: string;
}
