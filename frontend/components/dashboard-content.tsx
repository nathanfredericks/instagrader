"use client";

import useSWR from "swr";

import { client } from "@/lib/api/client";
import { ScoreDistributionChart } from "@/components/dashboard/score-distribution-chart";
import { EssayStatusChart } from "@/components/dashboard/essay-status-chart";
import { AssignmentProgressCards } from "@/components/dashboard/assignment-progress-cards";
import { RecentActivityTimeline } from "@/components/dashboard/recent-activity-timeline";
import type { DashboardResponse } from "@/lib/types";

export function DashboardContent({
  initialData,
}: {
  initialData: DashboardResponse;
}) {
  const { data: dashboard } = useSWR(
    "/api/dashboard/",
    async () => {
      const { data } = await client.GET("/api/dashboard/");
      return data;
    },
    { fallbackData: initialData, refreshInterval: 30000 }
  );

  if (!dashboard) return null;

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <ScoreDistributionChart data={dashboard.score_distribution} />
        <EssayStatusChart data={dashboard.essay_status_counts} />
      </div>
      <AssignmentProgressCards data={dashboard.active_assignments} />
      <RecentActivityTimeline activities={dashboard.recent_activity} />
    </div>
  );
}
