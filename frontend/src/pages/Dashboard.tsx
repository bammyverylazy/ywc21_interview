import { useCallback } from "react";
import { AppLayout } from "../components/layout/AppLayout";
import { SummaryCards } from "../components/dashboard/SummaryCards";
import { AttentionItems } from "../components/dashboard/AttentionItems";
import { RecentActivity } from "../components/dashboard/RecentActivity";
import { LatestNotices } from "../components/dashboard/LatestNotices";
import { RunMatchingButton } from "../components/dashboard/RunMatchingButton";
import { PageError } from "../components/ui/PageError";
import { DemoDataTag } from "../components/feedback/DemoDataTag";
import { useAsync } from "../hooks/useAsync";
import * as svc from "../services";
import { isMockData } from "../services";

export default function Dashboard() {
  const summary  = useAsync(svc.getDashboardSummary);
  const attention = useAsync(svc.getAttentionItems);
  const activity  = useAsync(svc.getRecentActivity);
  const notices   = useAsync(() => svc.getNotices());

  // Refetch everything after a matching run
  const refetchAll = useCallback(() => {
    summary.refetch(); attention.refetch(); activity.refetch(); notices.refetch();
  }, [summary, attention, activity, notices]);

  const topError = summary.error ?? attention.error ?? activity.error ?? notices.error;

  return (
    <AppLayout
      title="ภาพรวมระบบ"
      actions={isMockData ? <DemoDataTag /> : undefined}
    >
      {/* Run matching quick action */}
      <div className="mb-6">
        <RunMatchingButton onComplete={refetchAll} />
      </div>

      {/* Global error (non-fatal: still renders cards below) */}
      {topError && !summary.loading && (
        <PageError message={topError} onRetry={refetchAll} />
      )}

      {/* Summary stats */}
      <SummaryCards data={summary.data} loading={summary.loading} />

      {/* Two-column grid: attention + recent activity */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <AttentionItems items={attention.data} loading={attention.loading} />
        <RecentActivity logs={activity.data}   loading={activity.loading} />
      </div>

      {/* Latest notices */}
      <div className="mt-6">
        <LatestNotices notices={notices.data?.slice(0, 5) ?? null} loading={notices.loading} />
      </div>
    </AppLayout>
  );
}
