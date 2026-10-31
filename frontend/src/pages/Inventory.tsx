import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Search } from "lucide-react";
import { AppLayout } from "../components/layout/AppLayout";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { Skeleton } from "../components/ui/Skeleton";
import { PageError } from "../components/ui/PageError";
import { EmptyState } from "../components/feedback/EmptyState";
import { DemoDataTag } from "../components/feedback/DemoDataTag";
import { ProductForm } from "../components/inventory/ProductForm";
import { formatThaiDate } from "../lib/th";
import { useAsync } from "../hooks/useAsync";
import * as svc from "../services";
import { isMockData } from "../services";

export default function Inventory() {
  const [search, setSearch] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const { data: products, loading, error, refetch } = useAsync(svc.getProducts);

  const filtered = (products ?? []).filter((p) => {
    const q = search.toLowerCase();
    return p.brand_name.toLowerCase().includes(q) || (p.generic_name ?? "").toLowerCase().includes(q) || (p.registration_no ?? "").toLowerCase().includes(q);
  });

  return (
    <AppLayout title="คลังยา" breadcrumb={[{ label: "คลังยา", to: "/inventory" }]}
      actions={<>{isMockData && <DemoDataTag />}<Button icon={<Plus className="h-4 w-4" />} onClick={() => setAddOpen(true)}>เพิ่มผลิตภัณฑ์</Button></>}>

      {/* Search */}
      <div className="mb-5 max-w-sm">
        <Input label="ค้นหาผลิตภัณฑ์" id="inv-search" value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="ชื่อการค้า, ชื่อสามัญ, เลขทะเบียน…"
          className="pl-9" />
        <Search className="pointer-events-none absolute left-3 top-[2.15rem] h-4 w-4 text-muted-strong" aria-hidden="true" />
      </div>

      {error && <PageError message={error} onRetry={refetch} />}

      {/* Table */}
      {loading
        ? <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-14" />)}</div>
        : filtered.length === 0
          ? <EmptyState title="ไม่พบผลิตภัณฑ์" hint={search ? "ลองใช้คำค้นอื่น" : "เพิ่มผลิตภัณฑ์แรกเพื่อเริ่มตรวจสอบ"} action={!search && <Button icon={<Plus className="h-4 w-4" />} onClick={() => setAddOpen(true)}>เพิ่มผลิตภัณฑ์</Button>} />
          : (
            <div className="overflow-x-auto rounded-panel border border-line bg-white">
              <table className="w-full text-sm">
                <thead><tr className="border-b border-line bg-canvas-alt text-left text-xs text-muted-strong">
                  <th className="px-5 py-3 font-medium">ชื่อการค้า</th>
                  <th className="hidden px-5 py-3 font-medium sm:table-cell">ชื่อสามัญ</th>
                  <th className="hidden px-5 py-3 font-medium md:table-cell">เลขทะเบียน</th>
                  <th className="hidden px-5 py-3 font-medium lg:table-cell">บันทึกเมื่อ</th>
                  <th className="px-5 py-3" />
                </tr></thead>
                <tbody className="divide-y divide-line">
                  {filtered.map((p) => (
                    <tr key={p._id} className="hover:bg-canvas-alt">
                      <td className="px-5 py-3 font-medium">{p.brand_name}{p.data_origin === "demo" && <span className="ml-2 text-xs font-normal text-muted-strong">DEMO</span>}</td>
                      <td className="hidden px-5 py-3 text-muted-strong sm:table-cell">{p.generic_name ?? "—"}</td>
                      <td className="hidden px-5 py-3 text-muted-strong md:table-cell">{p.registration_no ?? <span className="italic">ไม่ระบุ</span>}</td>
                      <td className="hidden px-5 py-3 text-muted-strong lg:table-cell">{formatThaiDate(p.created_at)}</td>
                      <td className="px-5 py-3 text-right"><Link to={`/inventory/${p._id}`} className="text-brand hover:underline">ดูรายละเอียด</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="เพิ่มผลิตภัณฑ์ใหม่">
        <ProductForm onSaved={() => { setAddOpen(false); refetch(); }} onCancel={() => setAddOpen(false)} />
      </Modal>
    </AppLayout>
  );
}
