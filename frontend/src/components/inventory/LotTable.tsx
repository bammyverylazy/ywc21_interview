import { useState } from "react";
import { Edit2, Plus, Trash2 } from "lucide-react";
import type { InventoryItem } from "../../types/inventory";
import type { Product } from "../../types/product";
import { formatThaiDate } from "../../lib/th";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { ConfirmDialog } from "../ui/ConfirmDialog";
import { EmptyState } from "../feedback/EmptyState";
import { DemoDataTag } from "../feedback/DemoDataTag";
import { InventoryItemForm } from "./InventoryItemForm";
import * as svc from "../../services";

interface Props { product: Product; items: InventoryItem[]; onChanged: () => void; }
export function LotTable({ product, items, onChanged }: Props) {
  const [addOpen, setAddOpen]     = useState(false);
  const [editing, setEditing]     = useState<InventoryItem | null>(null);
  const [deleting, setDeleting]   = useState<InventoryItem | null>(null);
  const [delLoading, setDelLoading] = useState(false);

  const handleDelete = async () => {
    if (!deleting) return;
    setDelLoading(true);
    try { await svc.deleteInventoryItem(deleting._id); onChanged(); setDeleting(null); }
    catch { /* errors visible via PageError on parent */ }
    finally { setDelLoading(false); }
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <h3 className="font-medium">รุ่นการผลิต ({items.length})</h3>
        <Button size="md" icon={<Plus className="h-4 w-4" />} onClick={() => setAddOpen(true)}>เพิ่มรุ่นการผลิต</Button>
      </div>

      {items.length === 0
        ? <EmptyState title="ยังไม่มีรุ่นการผลิต" hint="เพิ่มเลข Lot/Batch เพื่อเพิ่มความแม่นยำในการตรวจสอบ" action={<Button size="md" icon={<Plus className="h-4 w-4" />} onClick={() => setAddOpen(true)}>เพิ่มรุ่นการผลิตแรก</Button>} />
        : (
          <div className="overflow-x-auto rounded-app border border-line">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line bg-canvas-alt text-left text-xs text-muted-strong">
                <th className="px-4 py-3 font-medium">เลขรุ่นการผลิต</th>
                <th className="px-4 py-3 font-medium">จำนวน</th>
                <th className="px-4 py-3 font-medium">วันหมดอายุ</th>
                <th className="px-4 py-3 font-medium">บันทึกเมื่อ</th>
                <th className="px-4 py-3" />
              </tr></thead>
              <tbody className="divide-y divide-line">
                {items.map((item) => (
                  <tr key={item._id} className="hover:bg-canvas-alt">
                    <td className="px-4 py-3 font-medium">
                      {item.lot_number ?? <span className="text-muted-strong">ไม่ระบุ</span>}
                      {item.is_demo && <DemoDataTag className="ml-2 align-middle" />}
                    </td>
                    <td className="px-4 py-3">{item.quantity} หน่วย</td>
                    <td className="px-4 py-3">{formatThaiDate(item.expiry_date)}</td>
                    <td className="px-4 py-3 text-muted-strong">{formatThaiDate(item.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button type="button" onClick={() => setEditing(item)} className="grid h-8 w-8 place-items-center rounded-app hover:bg-canvas-alt" aria-label={`แก้ไข ${item.lot_number ?? "รุ่นนี้"}`}><Edit2 className="h-3.5 w-3.5 text-muted-strong" /></button>
                        <button type="button" onClick={() => setDeleting(item)} className="grid h-8 w-8 place-items-center rounded-app hover:bg-danger-soft" aria-label={`ลบ ${item.lot_number ?? "รุ่นนี้"}`}><Trash2 className="h-3.5 w-3.5 text-danger" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="เพิ่มรุ่นการผลิต">
        <InventoryItemForm product={product} onSaved={() => { setAddOpen(false); onChanged(); }} onCancel={() => setAddOpen(false)} />
      </Modal>
      <Modal open={!!editing} onClose={() => setEditing(null)} title="แก้ไขรุ่นการผลิต">
        {editing && <InventoryItemForm product={product} item={editing} onSaved={() => { setEditing(null); onChanged(); }} onCancel={() => setEditing(null)} />}
      </Modal>
      <ConfirmDialog open={!!deleting} onClose={() => setDeleting(null)} onConfirm={handleDelete} loading={delLoading}
        title="ลบรุ่นการผลิต" message={`ต้องการลบรุ่นการผลิต "${deleting?.lot_number ?? "ไม่ระบุ"}" ออกจากระบบหรือไม่? การดำเนินการนี้ไม่สามารถย้อนกลับได้`} confirmLabel="ลบรุ่นการผลิต" />
    </>
  );
}
