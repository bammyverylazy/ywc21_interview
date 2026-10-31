import { useParams, Link } from "react-router-dom";
import { ExternalLink, CheckCircle2, XCircle } from "lucide-react";
import { AppLayout } from "../components/layout/AppLayout";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/Skeleton";
import { PageError } from "../components/ui/PageError";
import { Badge } from "../components/ui/Badge";
import { DemoDataTag } from "../components/feedback/DemoDataTag";
import { NOTICE_TYPE_LABEL, formatThaiDate } from "../lib/th";
import { getAffectedLotNumber } from "../types/notice";
import { useAsync } from "../hooks/useAsync";
import * as svc from "../services";
import { isMockData } from "../services";
import type { FieldProvenance, SafetyNotice } from "../types/notice";

const PROVENANCE_LABEL: Record<FieldProvenance["origin"], string> = {
  source_provided: "ข้อมูลจากรายการต้นทาง · ยังต้องทบทวน",
  machine_classified: "จัดประเภทโดยระบบ · ยังต้องทบทวน",
  machine_extracted: "สกัดจากเอกสารโดยระบบ · ยังต้องทบทวน",
  manually_verified: "ผู้ดูแลตรวจเทียบแหล่งทางการแล้ว",
  manual_unverified: "ป้อนหรือแก้ไขเอง · ยังไม่ยืนยัน",
  missing: "ไม่มีข้อมูลจากแหล่งที่ดึงมา",
};

function ProvenanceNote({ notice, field }: { notice: SafetyNotice; field: string }) {
  const provenance = notice.field_provenance?.[field];
  if (!provenance) {
    return <p className="mt-1 text-xs text-muted-strong">ไม่พบข้อมูลที่มาระดับฟิลด์</p>;
  }
  return (
    <p className="mt-1 text-xs text-muted-strong">
      {PROVENANCE_LABEL[provenance.origin]}
      {provenance.source_fields.length > 0 && ` · ฟิลด์ต้นทาง: ${provenance.source_fields.join(", ")}`}
    </p>
  );
}

export default function AlertDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: notice, loading, error, refetch } = useAsync(() => svc.getNotice(id!), [id]);

  if (loading) return <AppLayout title="กำลังโหลด…" breadcrumb={[{ label: "ประกาศแจ้งเตือน", to: "/alerts" }, { label: "…", to: "#" }]}><Skeleton className="h-64" /></AppLayout>;
  if (error || !notice) return <AppLayout title="ไม่พบประกาศ" breadcrumb={[{ label: "ประกาศแจ้งเตือน", to: "/alerts" }, { label: "ไม่พบ", to: "#" }]}><PageError message={error ?? "ไม่พบประกาศ"} onRetry={refetch} /></AppLayout>;

  const completeness = [
    ["ชื่อสามัญ", Boolean(notice.generic_name)],
    ["เลขทะเบียน", Boolean(notice.registration_no)],
    ["ผู้ผลิต", Boolean(notice.manufacturer)],
    ["วันที่เผยแพร่", Boolean(notice.published_at)],
    ["ข้อมูลรุ่นการผลิต", notice.affected_lots.length > 0],
  ] as const;
  const fields: { label: string; key: string; value: string | null | undefined; wide?: boolean }[] = [
    { label: "ชื่อผลิตภัณฑ์", key: "product_name", value: notice.product_name },
    { label: "ชื่อผลิตภัณฑ์ (ไทย)", key: "product_name_th", value: notice.product_name_th },
    { label: "ชื่อผลิตภัณฑ์ (อังกฤษ)", key: "product_name_en", value: notice.product_name_en },
    { label: "ชื่อสามัญ", key: "generic_name", value: notice.generic_name },
    { label: "เลขทะเบียน", key: "registration_no", value: notice.registration_no },
    { label: "ผู้ผลิต", key: "manufacturer", value: notice.manufacturer },
    { label: "รูปแบบยา", key: "dosage_form", value: notice.dosage_form },
    { label: "ความแรงหรือสารสำคัญที่ อย. ระบุ", key: "product_strength", value: notice.product_strength },
    { label: "ประเภทประกาศ", key: "notice_type", value: NOTICE_TYPE_LABEL[notice.notice_type] },
    { label: "วันที่เผยแพร่", key: "published_at", value: notice.published_at ? formatThaiDate(notice.published_at) : null },
    { label: "เหตุผลหรือปัญหาด้านความปลอดภัย", key: "reason", value: notice.reason, wide: true },
    { label: "การดำเนินการ", key: "recall_action", value: notice.recall_action },
    { label: "ผลกระทบ", key: "impact", value: notice.impact },
  ];

  return (
    <AppLayout title={notice.product_name}
      breadcrumb={[{ label: "ประกาศแจ้งเตือน", to: "/alerts" }, { label: notice.product_name, to: `/alerts/${id}` }]}
      actions={isMockData ? <DemoDataTag /> : undefined}>

      {/* Header card */}
      <Card className="mb-6 p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge color={notice.notice_type === "RECALL" ? "danger" : "warn"}>{NOTICE_TYPE_LABEL[notice.notice_type]}</Badge>
              {notice.verification_status === "verified" && <Badge color="brand">ตรวจสอบแหล่งทางการแล้ว</Badge>}
              {notice.record_origin === "manual" && <Badge color="warn">รายการป้อนเอง · ยังไม่ยืนยัน</Badge>}
              {notice.record_origin === "automatic_sync" && <Badge color="warn">ซิงค์อัตโนมัติ · ตรวจทานข้อมูล</Badge>}
              <span className="text-xs text-muted-strong">
                วันที่เผยแพร่ {notice.published_at ? formatThaiDate(notice.published_at) : "ไม่มีข้อมูล"}
                {" · "}นำเข้าระบบ {formatThaiDate(notice.imported_at)}
                {" · "}ตรวจจากแหล่งล่าสุด {notice.last_checked_at ? formatThaiDate(notice.last_checked_at) : "ไม่มีข้อมูล"}
              </span>
              {notice.source_created_at && <span className="mt-1 block text-xs text-muted-strong">วันที่สร้างรายการในระบบต้นทาง {formatThaiDate(notice.source_created_at)} (ไม่ใช่วันที่เผยแพร่)</span>}
            </div>
            <h2 className="mt-2 text-lg font-semibold">{notice.title}</h2>
            <p className="mt-1 text-sm text-muted-strong">แหล่งข้อมูล: {notice.source_name}</p>
          </div>
          <a href={notice.source_url} target="_blank" rel="noreferrer noopener"
            className="flex shrink-0 items-center gap-1.5 rounded-app border border-line bg-white px-3 py-2 text-sm hover:bg-canvas-alt">
          <ExternalLink className="h-4 w-4" aria-hidden="true" />{notice.record_origin === "automatic_sync" ? "เปิดหน้ารายการ อย." : "เปิดประกาศต้นฉบับ"}
          </a>
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Product info */}
        <Card className="p-5 lg:col-span-2">
          <h3 className="mb-4 font-semibold">ข้อมูลผลิตภัณฑ์จากประกาศ</h3>
          <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
            {fields.map(({ label, key, value, wide }) => (
              <div key={key} className={wide ? "sm:col-span-2" : ""}>
                <dt className="text-xs text-muted-strong">{label}</dt>
                <dd className="mt-0.5 text-sm font-medium">{value || <span className="font-normal italic text-muted-strong">ไม่มีข้อมูล</span>}</dd>
                <ProvenanceNote notice={notice} field={key} />
              </div>
            ))}
          </dl>

          {/* Affected lots */}
          <div className="mt-5 border-t border-line pt-4">
            <h4 className="mb-2 text-sm font-medium">รุ่นการผลิตที่ระบุในประกาศ</h4>
            {notice.affected_lots.length > 0
              ? <ul className="space-y-2">{notice.affected_lots.map((lot, index) => {
                const lotRecord = typeof lot === "string" ? { lot_number: lot } : lot;
                return (
                  <li key={`${lotRecord.lot_number}-${index}`} className="rounded-app bg-danger-soft px-3 py-2 text-sm">
                    <strong className="text-danger">LOT {getAffectedLotNumber(lot)}</strong>
                    <div className="mt-1 text-xs text-muted-strong">
                      วันที่ผลิต {lotRecord.manufacturing_date ? formatThaiDate(lotRecord.manufacturing_date) : "ไม่มีข้อมูล"}
                      {" · "}วันหมดอายุ {lotRecord.expiry_date ? formatThaiDate(lotRecord.expiry_date) : "ไม่มีข้อมูล"}
                    </div>
                    <p className="mt-1 text-xs text-muted-strong">
                      {lotRecord.verification_status === "verified"
                        ? "ผู้ดูแลตรวจสอบข้อมูล LOT แล้ว"
                        : lotRecord.extraction_method
                          ? "ข้อมูล LOT สกัดจากแหล่งต้นทางโดยระบบ · ยังต้องตรวจทาน"
                          : "ไม่มีข้อมูลวิธีสกัดหรือสถานะการตรวจสอบ"}
                      {lotRecord.source_reference && (
                        <>
                          {" · "}
                          <a
                            href={lotRecord.source_reference}
                            target="_blank"
                            rel="noreferrer noopener"
                            className="text-brand hover:underline"
                          >
                            แหล่งอ้างอิง
                          </a>
                        </>
                      )}
                    </p>
                  </li>
                );
              })}</ul>
              : <p className="text-sm italic text-muted-strong">ไม่มีข้อมูล LOT ในข้อมูลที่นำเข้าจากแหล่งต้นทาง ไม่ได้ยืนยันว่าประกาศต้นฉบับไม่มี LOT</p>}
            <ProvenanceNote notice={notice} field="affected_lots" />
          </div>
          {notice.affected_lots.some((lot) => typeof lot !== "string" && lot.extraction_method) && (
            <p className="mt-2 text-xs text-muted-strong">
              ข้อมูล LOT ที่ดึงจากรายละเอียด อย. ยังต้องตรวจทานกับประกาศต้นฉบับ
            </p>
          )}

          <div className="mt-5 border-t border-line pt-4">
            <h4 className="mb-2 text-sm font-medium">ไฟล์แนบจาก อย.</h4>
            {notice.attachments?.length ? (
              <ul className="space-y-2">
                {notice.attachments.map((attachment, index) => (
                  <li key={`${attachment.file_url}-${index}`} className="rounded-app bg-canvas-alt px-3 py-2 text-sm">
                    <a href={attachment.file_url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-brand hover:underline">
                      <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                      {attachment.original_filename || attachment.name || "เปิดไฟล์แนบ"}
                    </a>
                    {attachment.name && <span className="ml-2 text-xs text-muted-strong">{attachment.name}</span>}
                    <p className="mt-1 text-xs text-muted-strong">
                      {attachment.verification_status === "verified"
                        ? "ผู้ดูแลตรวจสอบรายการไฟล์แล้ว · ยังไม่ได้ยืนยันว่าไฟล์เปิดได้หรือเนื้อหาถูกต้อง"
                        : "ระบุโดยรายการ อย. · ยังไม่ได้ยืนยันว่าเปิดไฟล์ได้หรือข้อมูลในไฟล์ถูกต้อง"}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm italic text-muted-strong">
                {notice.source_attachments_status === "none"
                  ? "รายการไฟล์แนบที่ตรวจสอบไม่พบไฟล์ ไม่ได้ยืนยันว่าไม่มีเอกสารในทุกส่วนของแหล่งต้นทาง"
                  : notice.source_attachments_status === "failed"
                    ? "ดึงรายการไฟล์แนบไม่สำเร็จ จึงยังสรุปไม่ได้ว่าแหล่งต้นทางมีไฟล์หรือไม่"
                    : "ไม่มีข้อมูลไฟล์แนบที่ดึงมา ไม่ได้ยืนยันว่าแหล่งต้นทางไม่มีไฟล์"}
              </p>
            )}
          </div>

          {notice.source_id && <p className="mt-4 text-xs text-muted-strong">รหัสรายการต้นทาง: {notice.source_id}</p>}
          {notice.source_detail_id && <p className="mt-1 text-xs text-muted-strong">รหัสรายละเอียดต้นทาง: {notice.source_detail_id}</p>}
          {notice.source_detail_status === "partial" && (
            <p className="mt-2 text-xs text-warn">
              ระบบ อย. ส่งผลสถานะไม่สมบูรณ์ แต่มีข้อมูลรายละเอียดบางส่วน ข้อมูลที่แสดงยังต้องตรวจสอบกับแหล่งทางการ
            </p>
          )}
          {notice.source_detail_status === "failed" && (
            <p className="mt-2 text-xs text-warn">
              ดึงรายละเอียดจากแหล่ง อย. ไม่สำเร็จ รายการนี้ยังอาศัยข้อมูลจากหน้ารายการ
            </p>
          )}
        </Card>

        {/* Completeness + actions */}
        <div className="space-y-4">
          <Card className="p-5">
            <h3 className="mb-3 font-semibold text-sm">ความครบถ้วนของข้อมูล</h3>
            <ul className="space-y-2">
              {completeness.map(([k, v]) => (
                <li key={k} className="flex items-center gap-2 text-sm">
                  {v ? <CheckCircle2 className="h-4 w-4 shrink-0 text-brand" aria-label="มีข้อมูล" /> : <XCircle className="h-4 w-4 shrink-0 text-muted-strong" aria-label="ไม่มีข้อมูล" />}
                  {k}
                </li>
              ))}
            </ul>
          </Card>
          <Card className="p-5">
            <h3 className="mb-3 font-semibold text-sm">ผลการตรวจสอบ</h3>
            <Link to={`/matches?notice_id=${id}`} className="text-sm text-brand hover:underline">ดูผลการตรวจสอบที่เกี่ยวข้อง</Link>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
