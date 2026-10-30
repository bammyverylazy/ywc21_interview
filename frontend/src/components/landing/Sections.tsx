import { Link } from "react-router-dom";
import { Check, ExternalLink, X } from "lucide-react";
import { Logo } from "../brand/Logo";
import { Disclaimer } from "../feedback/Disclaimer";
import { MatchStatusBadge } from "../feedback/StatusBadge";
import { DemoDataTag } from "../feedback/DemoDataTag";
import { DashboardPreview } from "./DashboardPreview";
const wrap = "mx-auto max-w-6xl px-5 sm:px-8";
const h2 = "text-3xl font-light leading-[1.3] tracking-tight sm:text-5xl sm:leading-[1.25]";
const cta = "inline-flex h-12 items-center rounded-full px-7 text-base font-medium";

export function Hero() {
  return (
    <section id="top" className="relative overflow-hidden pb-24 pt-16 sm:pt-24">
      <div aria-hidden="true" className="absolute right-[-10%] top-[28%] h-[420px] w-[620px] rounded-full bg-brand-soft/70 blur-3xl" />
      <div className={`${wrap} relative`}>
        <h1 className="max-w-4xl text-4xl font-light leading-[1.3] tracking-tight sm:text-6xl sm:leading-[1.25] lg:text-7xl lg:leading-[1.2]">
          ติดตามประกาศยา<br />ตรวจสอบคลังได้ในที่เดียว
        </h1>
        <div className="mt-8 grid gap-8 lg:grid-cols-12">
          <p className="max-w-xl text-lg text-muted-strong lg:col-span-5 lg:col-start-1">
            YaSafe ช่วยเชื่อมโยงประกาศแจ้งเตือนด้านความปลอดภัยของยาเข้ากับข้อมูลยาและรุ่นการผลิตในคลังของร้านขายยา เพื่อให้ตรวจสอบและติดตามการดำเนินการได้ง่ายขึ้น
          </p>
          <div className="flex flex-wrap items-start gap-3 lg:col-span-6 lg:col-start-7 lg:justify-end">
            <Link to="/dashboard" className={`${cta} bg-brand text-white hover:bg-brand-dark`}>เปิดระบบจัดการ</Link>
            <a href="#about" className={`${cta} border border-line bg-white hover:bg-canvas-alt`}>รู้จักยาเซฟ</a>
          </div>
        </div>
      </div>
      <div className={`${wrap} relative mt-16`}>
        <div className="relative lg:ml-[14%] lg:mr-[-8%]">
          <DashboardPreview />
          <div className="glass absolute -left-2 top-[38%] hidden w-64 rounded-panel p-4 sm:block lg:-left-24">
            <p className="text-xs text-muted-strong">ประกาศตัวอย่าง</p>
            <p className="mt-1 text-sm font-medium">เรียกคืนผลิตภัณฑ์ ยาตัวอย่าง A</p>
            <p className="mt-2 text-xs text-muted-strong">ระบุรุ่นการผลิตที่เกี่ยวข้อง 1 รุ่น · มีลิงก์ต้นฉบับ</p>
          </div>
          <div className="glass absolute -bottom-6 right-4 hidden w-72 rounded-panel p-4 sm:block lg:right-10">
            <MatchStatusBadge status="EXACT_MATCH" />
            <p className="mt-2 text-xs leading-relaxed">เลขทะเบียนและเลขรุ่นการผลิตตรงกับประกาศ ควรตรวจสอบกับต้นฉบับและเภสัชกรผู้รับผิดชอบ</p>
          </div>
        </div>
      </div>
    </section>
  );
}

const VALUES = [
  ["จัดการข้อมูลยาในคลัง", "บันทึกยาแต่ละรายการพร้อมเลขทะเบียน จำนวน วันหมดอายุ และเลขรุ่นการผลิตทีละรุ่น เพื่อให้ระบุได้ว่ารุ่นใดในคลังที่เกี่ยวข้อง"],
  ["ติดตามประกาศแจ้งเตือน", "เก็บประกาศที่นำเข้าจากแหล่งทางการ พร้อมวันที่เผยแพร่ เหตุผล รุ่นการผลิตที่ระบุ และลิงก์ไปยังประกาศต้นฉบับ"],
  ["ตรวจสอบและติดตามผล", "ระบบเทียบคลังกับประกาศและอธิบายเหตุผลของผลลัพธ์ จากนั้นเจ้าหน้าที่บันทึกสถานะและการดำเนินการไว้ย้อนดูได้"],
];
export function Value() {
  return (
    <section id="about" className="border-t border-line py-24">
      <div className={`${wrap} grid gap-12 lg:grid-cols-12`}>
        <h2 className={`${h2} lg:col-span-5`}>ประกาศยาจำนวนมาก แต่ร้านมีเพียงบางรุ่นที่เกี่ยวข้อง</h2>
        <ul className="lg:col-span-7">
          {VALUES.map(([t, d]) => (
            <li key={t} className="border-t border-line py-7 first:border-t-0 first:pt-0">
              <h3 className="text-xl font-medium">{t}</h3><p className="mt-2 max-w-xl text-muted-strong">{d}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

const STEPS = [
  ["บันทึกข้อมูลยาและรุ่นการผลิตในคลัง", "เพิ่มยาและแยกบันทึกแต่ละรุ่นการผลิต ประกาศที่ระบุเพียงบางรุ่นจะได้ไม่ทำให้ทุกรุ่นของยานั้นถูกระบุว่าเกี่ยวข้อง"],
  ["ตรวจสอบข้อมูลกับประกาศแจ้งเตือน", "สั่งให้ระบบเทียบคลังกับประกาศที่บันทึกไว้ ได้ผล 3 แบบ คือพบรายการตรงกัน พบรายการที่อาจเกี่ยวข้อง และไม่พบรายการที่ตรงกัน"],
  ["ตรวจสอบผลและบันทึกการดำเนินการ", "เปิดดูเหตุผลคู่กับประกาศต้นฉบับ แล้วบันทึกสถานะ เช่น ตรวจสอบแล้ว หรือส่งต่อ พร้อมหมายเหตุ ประวัติจะไม่ถูกเขียนทับ"],
];
export function HowItWorks() {
  return (
    <section id="how" className="bg-canvas-alt py-24">
      <div className={`${wrap} grid gap-12 lg:grid-cols-12`}>
        <div className="lg:col-span-4"><h2 className={`${h2} lg:sticky lg:top-28`}>สามขั้นตอนในการตรวจสอบ</h2></div>
        <ol className="relative space-y-12 lg:col-span-8 lg:pl-10">
          <span aria-hidden="true" className="absolute bottom-4 left-[19px] top-4 hidden w-px bg-line lg:block" />
          {STEPS.map(([t, d], i) => (
            <li key={t} className="relative flex gap-5">
              <span className="relative z-10 grid h-10 w-10 shrink-0 place-items-center rounded-full border border-line bg-white text-sm font-semibold text-brand lg:-ml-10">{i + 1}</span>
              <div><h3 className="text-xl font-medium">{t}</h3><p className="mt-2 max-w-xl text-muted-strong">{d}</p></div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

export function Showcase() {
  return (
    <section id="features" className="py-24">
      <div className={wrap}>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <h2 className={`${h2} max-w-2xl`}>เห็นหลักฐานของทุกผลลัพธ์</h2><DemoDataTag />
        </div>
        <div aria-hidden="true" className="mt-12 grid gap-5 lg:grid-cols-12">
          <div className="rounded-panel border border-line bg-white p-6 lg:col-span-8">
            <p className="text-sm font-medium">เปรียบเทียบรายการในคลังกับประกาศ</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {[["ในคลังของร้าน", [["เลขทะเบียน", "ตัวอย่าง-0001", true], ["เลขรุ่นการผลิต", "L-DEMO-01", true], ["ผู้ผลิต", "ไม่มีข้อมูล", false]]],
                ["ประกาศทางการ", [["เลขทะเบียน", "ตัวอย่าง-0001", true], ["เลขรุ่นการผลิต", "L-DEMO-01", true], ["ผู้ผลิต", "ผู้ผลิตตัวอย่าง", false]]]].map(([h, rows]) => (
                <div key={h as string} className="rounded-app bg-canvas-alt p-4">
                  <p className="text-xs text-muted-strong">{h as string}</p>
                  {(rows as [string, string, boolean][]).map(([k, v, ok]) => (
                    <div key={k} className={`mt-2 flex justify-between rounded-md px-2 py-1.5 text-sm ${ok ? "bg-brand-soft" : ""}`}><span className="text-muted-strong">{k}</span><span className="font-medium">{v}</span></div>
                  ))}
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-panel border border-line bg-white p-6 lg:col-span-4">
            <p className="text-sm font-medium">รายละเอียดประกาศ</p>
            <p className="mt-3 text-xs text-muted-strong">การเรียกคืนผลิตภัณฑ์ · เผยแพร่ 20 ต.ค. 2569</p>
            <p className="mt-2 text-sm">เหตุผล: ข้อมูลตัวอย่างสำหรับสาธิต</p>
            <span className="mt-4 inline-flex items-center gap-1.5 text-sm text-brand"><ExternalLink className="h-4 w-4" />เปิดประกาศต้นฉบับ</span>
          </div>
          <div className="rounded-panel border border-line bg-white p-6 lg:col-span-12">
            <p className="text-sm font-medium">ยาหนึ่งรายการ หลายรุ่นการผลิต</p>
            {[["L-DEMO-01", "30 หน่วย", "EXACT_MATCH"], ["L-DEMO-02", "20 หน่วย", "NO_MATCH"], ["L-DEMO-03", "15 หน่วย", "NO_MATCH"]].map(([l, q, s]) => (
              <div key={l} className="mt-2 flex items-center justify-between border-t border-line pt-2 text-sm"><span>{l}</span><span className="text-muted-strong">{q}</span><MatchStatusBadge status={s as "EXACT_MATCH" | "NO_MATCH"} /></div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

const DOES = ["ลิงก์และชื่อแหล่งของประกาศต้นฉบับ", "วันที่เผยแพร่ประกาศ", "ข้อมูลผลิตภัณฑ์และเลขรุ่นการผลิตเท่าที่ประกาศระบุ", "เหตุผลของผลการตรวจสอบแต่ละรายการ"];
const DOESNT = ["ไม่ได้รับประกันว่ายาที่ไม่พบรายการตรงกันนั้นปลอดภัย", "ไม่ตัดสินใจแทนว่าจะจำหน่าย ถอน หรือทำลายยา", "ไม่ได้ซิงก์ประกาศแบบเรียลไทม์ ประกาศถูกนำเข้าโดยผู้ดูแลระบบ"];
export function Transparency() {
  return (
    <section id="sources" className="bg-canvas-alt py-24">
      <div className={`${wrap} grid gap-12 lg:grid-cols-12`}>
        <div className="lg:col-span-5">
          <h2 className={h2}>เครื่องมือช่วยตัดสินใจ ไม่ใช่คำตัดสิน</h2>
          <p className="mt-6 max-w-md text-muted-strong">ผลที่เป็น “พบรายการที่อาจเกี่ยวข้อง” ต้องให้เจ้าหน้าที่ตรวจสอบเสมอ ข้อมูลที่ไม่ครบจะไม่ถูกตีความว่าปลอดภัย</p>
        </div>
        <div className="grid gap-8 sm:grid-cols-2 lg:col-span-7">
          <div><h3 className="font-medium">สิ่งที่แสดงให้ตรวจสอบได้</h3>
            <ul className="mt-4 space-y-3">{DOES.map((t) => <li key={t} className="flex gap-2 text-sm"><Check className="mt-0.5 h-4 w-4 shrink-0 text-brand" aria-hidden="true" />{t}</li>)}</ul></div>
          <div><h3 className="font-medium">ข้อจำกัดที่ควรรู้</h3>
            <ul className="mt-4 space-y-3">{DOESNT.map((t) => <li key={t} className="flex gap-2 text-sm"><X className="mt-0.5 h-4 w-4 shrink-0 text-muted-strong" aria-hidden="true" />{t}</li>)}</ul></div>
        </div>
      </div>
    </section>
  );
}

export function FinalCta() {
  return (
    <section className="relative overflow-hidden py-28">
      <div aria-hidden="true" className="absolute left-1/2 top-1/2 h-72 w-[560px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-soft blur-3xl" />
      <div className={`${wrap} relative`}>
        <h2 className={`${h2} max-w-3xl`}>ลองดูขั้นตอนทั้งหมดในพื้นที่สาธิต</h2>
        <p className="mt-5 max-w-lg text-muted-strong">พื้นที่สาธิตใช้ข้อมูลตัวอย่างที่ระบุไว้ชัดเจน ไม่ใช่ประกาศทางการ</p>
        <Link to="/dashboard" className={`${cta} glass mt-8 font-medium text-brand-dark hover:bg-white`}>เปิดระบบจัดการ</Link>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-line py-14">
      <div className={`${wrap} grid gap-10 lg:grid-cols-12`}>
        <div className="lg:col-span-5"><Logo /><p className="mt-4 max-w-sm text-sm text-muted-strong">ระบบช่วยเชื่อมโยงประกาศความปลอดภัยของยากับคลังยาและรุ่นการผลิตในร้านขายยาอิสระ</p></div>
        <nav aria-label="ลิงก์ท้ายหน้า" className="lg:col-span-3"><ul className="space-y-2 text-sm">
          {[["#about", "เกี่ยวกับยาเซฟ"], ["#how", "วิธีการทำงาน"], ["#features", "ฟีเจอร์"], ["#sources", "แหล่งข้อมูล"]].map(([h, l]) => <li key={h}><a href={h} className="hover:text-brand">{l}</a></li>)}</ul></nav>
        <p className="text-sm text-muted-strong lg:col-span-4">แหล่งข้อมูลประกาศ: ประกาศทางการของ อย. (สำนักงานคณะกรรมการอาหารและยา) ที่ผู้ดูแลนำเข้า พร้อมลิงก์ต้นฉบับ ข้อมูลในหน้านี้เป็นตัวอย่างเพื่อการสาธิต</p>
        <div className="lg:col-span-12"><Disclaimer /></div>
      </div>
    </footer>
  );
}
