import { AppLayout } from "../components/layout/AppLayout";
import { Skeleton } from "../components/ui/Skeleton";
// Full implementation in Milestone 6.
export default function MatchDetail() {
  return (
    <AppLayout title="รายละเอียดผลการตรวจสอบ" breadcrumb={[{ label: "ผลการตรวจสอบ", to: "/matches" }, { label: "รายละเอียด", to: "#" }]}>
      <Skeleton className="h-96" />
    </AppLayout>
  );
}
