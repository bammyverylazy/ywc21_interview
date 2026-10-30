import { Link } from "react-router-dom";
import { Logo } from "../components/brand/Logo";
/** Temporary target for /dashboard etc. until Milestone 3 builds the app layout. */
export default function AppPlaceholder() {
  return (
    <main className="grid min-h-screen place-items-center p-6 text-center">
      <div className="space-y-4"><Logo className="justify-center" /><p>ระบบจัดการอยู่ระหว่างการพัฒนา</p><Link to="/" className="text-brand underline">กลับหน้าแรก</Link></div>
    </main>
  );
}
