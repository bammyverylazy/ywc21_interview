export type NoticeType = "RECALL" | "WARNING";
export interface SafetyNotice {
  _id: string; title: string; notice_type: NoticeType; product_name: string; generic_name?: string | null;
  registration_no?: string | null; manufacturer?: string | null; affected_lots: string[]; reason?: string | null;
  published_at?: string | null; source_name: string; source_url: string; imported_at: string;
  data_completeness?: { has_registration_no: boolean; has_lot_information: boolean; has_manufacturer: boolean };
}
