export type NoticeType = "RECALL" | "WARNING";
export interface AffectedLot {
  lot_number: string;
  manufacturing_date?: string | null;
  expiry_date?: string | null;
  extraction_method?: string | null;
  verification_status?: "manual_review" | "verified" | null;
  source_reference?: string | null;
}
export interface NoticeAttachment {
  name?: string | null;
  original_filename?: string | null;
  file_url: string;
  source_reference?: string | null;
  extraction_method: string;
  verification_status: "manual_review" | "verified";
}
export interface FieldProvenance {
  origin:
    | "source_provided"
    | "machine_classified"
    | "machine_extracted"
    | "manually_verified"
    | "manual_unverified"
    | "missing";
  extraction_method: string;
  source_fields: string[];
  source_reference?: string | null;
  verification_status: "manual_review" | "verified";
}
export interface SafetyNotice {
  _id: string; title: string; notice_type: NoticeType; product_name: string; generic_name?: string | null;
  registration_no?: string | null; manufacturer?: string | null; affected_lots: (string | AffectedLot)[]; reason?: string | null;
  dosage_form?: string | null; product_strength?: string | null;
  attachments?: NoticeAttachment[];
  published_at?: string | null; source_name: string; source_url: string; imported_at: string;
  source_id?: string | null; product_name_th?: string | null; product_name_en?: string | null;
  source_detail_id?: string | null;
  source_detail_status?: "not_requested" | "available" | "partial" | "failed" | null;
  source_attachments_status?: "not_requested" | "available" | "none" | "failed" | null;
  recall_action?: string | null; impact?: string | null; record_origin?: "manual" | "verified_import" | "automatic_sync";
  verification_status?: "manual_review" | "verified";
  last_checked_at?: string | null; source_changed_at?: string | null; source_content_hash?: string | null;
  source_created_at?: string | null;
  field_provenance?: Record<string, FieldProvenance>;
  data_completeness?: { has_registration_no: boolean; has_lot_information: boolean; has_manufacturer: boolean };
}

export function getAffectedLotNumber(lot: string | AffectedLot): string {
  return typeof lot === "string" ? lot : lot.lot_number;
}
