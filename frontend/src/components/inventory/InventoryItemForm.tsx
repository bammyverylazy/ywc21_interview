import { useState } from "react";
import type { InventoryItem } from "../../types/inventory";
import type { Product } from "../../types/product";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";
import * as svc from "../../services";

type F = { lot_number: string; quantity: string; expiry_date: string };
type E = Partial<Record<keyof F, string>>;

function validate(f: F): E {
  const e: E = {};
  if (!f.quantity.trim() || Number(f.quantity) < 0 || !Number.isInteger(Number(f.quantity)))
    e.quantity = "จำนวนต้องเป็นจำนวนเต็มที่ไม่ติดลบ";
  if (!f.expiry_date) e.expiry_date = "กรุณาระบุวันหมดอายุ";
  return e;
}

interface Props { product: Product; item?: InventoryItem; onSaved: (i: InventoryItem) => void; onCancel: () => void; }
export function InventoryItemForm({ product, item, onSaved, onCancel }: Props) {
  const [form, setForm] = useState<F>({
    lot_number: item?.lot_number ?? "", quantity: String(item?.quantity ?? ""), expiry_date: item?.expiry_date ?? "",
  });
  const [errors, setErrors] = useState<E>({});
  const [saving, setSaving] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const set = (k: keyof F) => (ev: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [k]: ev.target.value }));

  const submit = async () => {
    const e = validate(form); setErrors(e);
    if (Object.keys(e).length) return;
    setSaving(true); setApiError(null);
    try {
      const payload = { product_id: product._id, lot_number: form.lot_number.trim() || null, quantity: Number(form.quantity), expiry_date: form.expiry_date };
      const saved = item
        ? await svc.updateInventoryItem(item._id, payload)
        : await svc.createInventoryItem(payload as Parameters<typeof svc.createInventoryItem>[0]);
      onSaved(saved as InventoryItem);
    } catch (err) { setApiError(err instanceof Error ? err.message : "บันทึกไม่สำเร็จ"); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-4">
      <p className="rounded-app bg-canvas-alt px-3 py-2 text-sm"><span className="text-muted-strong">ผลิตภัณฑ์:</span> {product.brand_name}</p>
      <Input label="เลขรุ่นการผลิต (Lot/Batch)" value={form.lot_number} onChange={set("lot_number")} placeholder="เช่น L25001" hint="ระบุเพื่อเพิ่มความแม่นยำในการตรวจสอบ ไม่บังคับ" />
      <Input label="จำนวน (หน่วย)" type="number" min="0" step="1" required value={form.quantity} onChange={set("quantity")} error={errors.quantity} />
      <Input label="วันหมดอายุ" type="date" required value={form.expiry_date} onChange={set("expiry_date")} error={errors.expiry_date} />
      {apiError && <p role="alert" className="text-sm text-danger">{apiError}</p>}
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel} disabled={saving}>ยกเลิก</Button>
        <Button onClick={submit} loading={saving}>{item ? "บันทึกการแก้ไข" : "เพิ่มรุ่นการผลิต"}</Button>
      </div>
    </div>
  );
}
