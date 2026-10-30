import { useState } from "react";
import type { Product } from "../../types/product";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";
import * as svc from "../../services";

type FormData = { brand_name: string; generic_name: string; registration_no: string; manufacturer: string };
type Errors   = Partial<Record<keyof FormData, string>>;

function validate(f: FormData): Errors {
  const e: Errors = {};
  if (!f.brand_name.trim()) e.brand_name = "กรุณาระบุชื่อการค้า";
  return e;
}

interface Props { product?: Product; onSaved: (p: Product) => void; onCancel: () => void; }
export function ProductForm({ product, onSaved, onCancel }: Props) {
  const [form, setForm] = useState<FormData>({
    brand_name: product?.brand_name ?? "", generic_name: product?.generic_name ?? "",
    registration_no: product?.registration_no ?? "", manufacturer: product?.manufacturer ?? "",
  });
  const [errors, setErrors] = useState<Errors>({});
  const [saving, setSaving] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const set = (k: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async () => {
    const e = validate(form); setErrors(e);
    if (Object.keys(e).length) return;
    setSaving(true); setApiError(null);
    try {
      const payload = {
        brand_name: form.brand_name.trim(),
        generic_name: form.generic_name.trim() || null,
        registration_no: form.registration_no.trim() || null,
        manufacturer: form.manufacturer.trim() || null,
      };
      const saved = product
        ? await svc.updateProduct(product._id, payload)
        : await svc.createProduct(payload as Parameters<typeof svc.createProduct>[0]);
      onSaved(saved as Product);
    } catch (err) { setApiError(err instanceof Error ? err.message : "บันทึกไม่สำเร็จ"); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-4">
      <Input label="ชื่อการค้า" required value={form.brand_name} onChange={set("brand_name")} error={errors.brand_name} placeholder="เช่น ยาตัวอย่าง แอลฟา" />
      <Input label="ชื่อสามัญ" value={form.generic_name} onChange={set("generic_name")} placeholder="เช่น Example Drug Alpha" hint="ไม่บังคับ" />
      <Input label="เลขทะเบียน" value={form.registration_no} onChange={set("registration_no")} placeholder="เช่น 1A 12/65" hint="จัดเก็บตามรูปแบบเดิม ไม่บังคับ" />
      <Input label="ผู้ผลิต" value={form.manufacturer} onChange={set("manufacturer")} placeholder="เช่น บริษัทตัวอย่าง จำกัด" hint="ไม่บังคับ" />
      {apiError && <p role="alert" className="text-sm text-danger">{apiError}</p>}
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel} disabled={saving}>ยกเลิก</Button>
        <Button onClick={submit} loading={saving}>{product ? "บันทึกการแก้ไข" : "เพิ่มผลิตภัณฑ์"}</Button>
      </div>
    </div>
  );
}
