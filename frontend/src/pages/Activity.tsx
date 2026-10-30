import { AppLayout } from "../components/layout/AppLayout";
import { Skeleton } from "../components/ui/Skeleton";
// Full implementation in Milestone 7.
export default function Activity() {
  return (
    <AppLayout title="ประวัติการดำเนินการ" breadcrumb={[{ label: "ประวัติการดำเนินการ", to: "/activity" }]}>
      <Skeleton className="h-96" />
    </AppLayout>
  );
}
