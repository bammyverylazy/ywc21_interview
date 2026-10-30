import { Link } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
export default function NotFound() {
  return (
    <AppLayout title="ไม่พบหน้า">
      <div className="flex flex-col items-center gap-3 py-24 text-center">
        <p className="text-4xl font-light text-muted-strong">404</p>
        <p className="font-medium">ไม่พบหน้าที่คุณต้องการ</p>
        <Link to="/dashboard" className="text-sm text-brand underline">กลับหน้าภาพรวม</Link>
      </div>
    </AppLayout>
  );
}
