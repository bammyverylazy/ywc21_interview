import { useState } from "react";
import type { SafetyNotice, NoticeType } from "../../types/notice";
import { Input, Textarea } from "../ui/Input";
import { Select } from "../ui/Select";
import { Button } from "../ui/Button";
import { NOTICE_TYPE_LABEL } from "../../lib/th";
import * as svc from "../../services";

type F = { title: string; notice_type: NoticeType; product_name: string; generic_name: string;
  registration_no: string; manufacturer: string; affected_lots: string; reason: string;
  published_at: string; source_name: string; source_url: string; };
type E = Partial<Record<keyof F, string>>;

function validate(f: F): E {
  const e: E = {};
  if (!f.title.trim()) e.title = "กรุณาระบุชื่อประกาศ";
  if (!f.product_name.trim()) e.product_name = "กรุณาระบุชื่อผลิตภัณฑ์";
  if (!f.source_name.trim()) e.source_name = "กรุณาระบุชื่อแหล่งข้อมูล";
  if (!f.source_url.trim()) e.source_url = "กรุณาระบุ URL ของประกาศต้นฉบับ";
  else { try { new URL(f.source_url); } catch { e.source_url = "รูปแบบ URL ไม่ถูกต้อง"; } }
  return e;
}

interface Props { onSaved: (n: SafetyNotice) => void; onCancel: () => void; }
export function NoticeForm({ onSaved, onCancel }: Props) {
  const [form, setForm] = useState<F>({ title: "", notice_type: "RECALL", product_name: "", generic_name: "", registration_no: "", manufacturer: "", affected_lots: "", reason: "", published_at: "", source_name: "", source_url: "" });
  const [errors, setErrors] = useState<E>({});
  const [saving, setSaving] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const set = (k: keyof F) => (ev: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setForm((f) => ({ ...f, [k]: ev.target.value }));

  const submit = async () => {
    const e = validate(form); setErrors(e);
    if (Object.keys(e).length) return;
    setSaving(true); setApiError(null);
    try {
      const lots = form.affected_lots.split(",").map((l) => l.trim()).filter(Boolean);
      const payload = {
        title: form.title.trim(), notice_type: form.notice_type, product_name: form.product_name.trim(),
        generic_name: form.generic_name.trim() || null, registration_no: form.registration_no.trim() || null,
        manufacturer: form.manufacturer.trim() || null, affected_lots: lots,
        reason: form.reason.trim() || null, published_at: form.published_at || null,
        source_name: form.source_name.trim(), source_url: form.source_url.trim(),
        data_completeness: { has_registration_no: !!form.registration_no.trim(), has_lot_information: lots.length > 0, has_manufacturer: !!form.manufacturer.trim() },
      };
      const saved = await svc.createNotice(payload as Parameters<typeof svc.createNotice>[0]);
      onSaved(saved as SafetyNotice);
    } catch (err) { setApiError(err instanceof Error ? err.message : "บันทึกไม่สำเร็จ"); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-4">
      <p className="rounded-app bg-warn-soft px-3 py-2 text-xs text-warn">นำเข้าเฉพาะประกาศจากแหล่งทางการเท่านั้น โปรดระบุ URL ต้นฉบับและวันที่เผยแพร่จริงเสมอ</p>
      <Select label="ประเภทประกาศ" value={form.notice_type} onChange={set("notice_type")} options={[{ value: "RECALL", label: NOTICE_TYPE_LABEL.RECALL }, { value: "WARNING", label: NOTICE_TYPE_LABEL.WARNING }]} />
      <Input label="ชื่อประกาศ" required value={form.title} onChange={set("title")} error={errors.title} placeholder="ชื่อประกาศตามเอกสารต้นฉบับ" />
      <Input label="ชื่อผลิตภัณฑ์" required value={form.product_name} onChange={set("product_name")} error={errors.product_name} />
      <Input label="ชื่อสามัญ" value={form.generic_name} onChange={set("generic_name")} hint="ไม่บังคับ" />
      <Input label="เลขทะเบียน" value={form.registration_no} onChange={set("registration_no")} hint="ระบุหากปรากฏในประกาศ" />
      <Input label="ผู้ผลิต" value={form.manufacturer} onChange={set("manufacturer")} hint="ไม่บังคับ" />
      <Input label="เลขรุ่นการผลิตที่เกี่ยวข้อง" value={form.affected_lots} onChange={set("affected_lots")} placeholder="L25001, L25002 (คั่นด้วยจุลภาค)" hint="เว้นว่างหากประกาศไม่ระบุ" />
      <Textarea label="เหตุผล / สาระสำคัญ" value={form.reason} onChange={set("reason")} />
      <Input label="วันที่เผยแพร่" type="date" value={form.published_at} onChange={set("published_at")} hint="ตามประกาศต้นฉบับ" />
      <Input label="ชื่อแหล่งข้อมูล" required value={form.source_name} onChange={set("source_name")} error={errors.source_name} placeholder="เช่น สำนักงานคณะกรรมการอาหารและยา" />
      <Input label="URL ประกาศต้นฉบับ" type="url" required value={form.source_url} onChange={set("source_url")} error={errors.source_url} placeholder="https://…" />
      {apiError && <p role="alert" className="text-sm text-danger">{apiError}</p>}
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel} disabled={saving}>ยกเลิก</Button>
        <Button onClick={submit} loading={saving}>นำเข้าประกาศ</Button>
      </div>
    </div>
  );
}
