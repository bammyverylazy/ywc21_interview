import { AppLayout } from "../components/layout/AppLayout";
import { Skeleton } from "../components/ui/Skeleton";
// Full implementation in Milestone 6.
export default function Matches() {
  return (
    <AppLayout title="ผลการตรวจสอบ" breadcrumb={[{ label: "ผลการตรวจสอบ", to: "/matches" }]}>
      <Skeleton className="h-10 w-64" /><Skeleton className="mt-4 h-96" />
    </AppLayout>
  );
}
