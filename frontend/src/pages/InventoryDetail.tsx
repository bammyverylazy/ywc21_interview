import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Edit2, Trash2 } from "lucide-react";
import { AppLayout } from "../components/layout/AppLayout";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Modal } from "../components/ui/Modal";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { Skeleton } from "../components/ui/Skeleton";
import { PageError } from "../components/ui/PageError";
import { LotTable } from "../components/inventory/LotTable";
import { ProductForm } from "../components/inventory/ProductForm";
import { formatThaiDate } from "../lib/th";
import { useAsync } from "../hooks/useAsync";
import * as svc from "../services";

export default function InventoryDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: product, loading, error, refetch } = useAsync(() => svc.getProduct(id!), [id]);
  const { data: items, loading: iLoading, refetch: iRefetch } = useAsync(() => svc.getInventory({ product_id: id }), [id]);
  const [editOpen, setEditOpen] = useState(false);
  const [delOpen,  setDelOpen]  = useState(false);
  const [delLoading, setDelLoading] = useState(false);

  const handleDelete = async () => {
    setDelLoading(true);
    try { await svc.deleteProduct(id!); window.location.href = "/inventory"; }
    catch { setDelLoading(false); }
  };

  if (loading) return <AppLayout title="กำลังโหลด…" breadcrumb={[{ label: "คลังยา", to: "/inventory" }, { label: "…", to: "#" }]}><Skeleton className="h-48" /></AppLayout>;
  if (error || !product) return <AppLayout title="ไม่พบข้อมูล" breadcrumb={[{ label: "คลังยา", to: "/inventory" }, { label: "ไม่พบ", to: "#" }]}><PageError message={error ?? "ไม่พบผลิตภัณฑ์"} onRetry={refetch} /></AppLayout>;

  const fields: [string, string | null | undefined][] = [
    ["ชื่อการค้า", product.brand_name], ["ชื่อสามัญ", product.generic_name],
    ["เลขทะเบียน", product.registration_no], ["ผู้ผลิต", product.manufacturer],
    ["บันทึกเมื่อ", formatThaiDate(product.created_at)], ["แก้ไขล่าสุด", formatThaiDate(product.updated_at)],
  ];

  return (
    <AppLayout title={product.brand_name}
      breadcrumb={[{ label: "คลังยา", to: "/inventory" }, { label: product.brand_name, to: `/inventory/${id}` }]}
      actions={
        <div className="flex gap-2">
          <Button variant="secondary" icon={<Edit2 className="h-4 w-4" />} onClick={() => setEditOpen(true)}>แก้ไข</Button>
          <Button variant="danger" icon={<Trash2 className="h-4 w-4" />} onClick={() => setDelOpen(true)}>ลบ</Button>
        </div>
      }>

      {/* Product info card */}
      <Card className="mb-6 p-5">
        <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
          {fields.map(([k, v]) => (
            <div key={k}><dt className="text-xs text-muted-strong">{k}</dt>
              <dd className="mt-0.5 text-sm font-medium">{v ?? <span className="font-normal text-muted-strong">ไม่มีข้อมูล</span>}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {/* Related matches quick-link */}
      <div className="mb-5 flex items-center justify-between">
        <h3 className="font-medium">ผลการตรวจสอบที่เกี่ยวข้อง</h3>
        <Link to={`/matches?product_id=${id}`} className="text-sm text-brand hover:underline">ดูผลการตรวจสอบ</Link>
      </div>

      {/* LOT table */}
      <div className="space-y-4">
        {iLoading
          ? <Skeleton className="h-48" />
          : <LotTable product={product} items={items ?? []} onChanged={() => { refetch(); iRefetch(); }} />}
      </div>

      {/* Modals */}
      <Modal open={editOpen} onClose={() => setEditOpen(false)} title="แก้ไขผลิตภัณฑ์">
        <ProductForm product={product} onSaved={() => { setEditOpen(false); refetch(); }} onCancel={() => setEditOpen(false)} />
      </Modal>
      <ConfirmDialog open={delOpen} onClose={() => setDelOpen(false)} onConfirm={handleDelete} loading={delLoading}
        title="ลบผลิตภัณฑ์" message={`ต้องการลบ "${product.brand_name}" และรุ่นการผลิตทั้งหมดออกจากระบบหรือไม่?`} confirmLabel="ลบผลิตภัณฑ์" />
    </AppLayout>
  );
}
