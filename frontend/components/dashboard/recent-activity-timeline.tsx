"use client";

import Link from "next/link";
import {
  AlertTriangleIcon,
  CheckCircle2Icon,
  FlagIcon,
  SparklesIcon,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { RecentActivityItem } from "@/lib/types";

const activityConfig: Record<
  string,
  { icon: React.ReactNode; label: (item: RecentActivityItem) => string }
> = {
  essay_graded: {
    icon: <SparklesIcon className="size-4 text-amber-500" />,
    label: (item) => `${item.essay_file_name} is ready for review`,
  },
  essay_reviewed: {
    icon: <CheckCircle2Icon className="size-4 text-green-500" />,
    label: (item) => `${item.essay_file_name} was reviewed`,
  },
  assignment_completed: {
    icon: <FlagIcon className="size-4 text-green-500" />,
    label: (item) => `${item.assignment_title} completed`,
  },
  essay_failed: {
    icon: <AlertTriangleIcon className="size-4 text-red-500" />,
    label: (item) => `${item.essay_file_name} failed to process`,
  },
};

// falls back to absolute date format after 7 days
function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMinutes < 1) return "just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function RecentActivityTimeline({
  activities,
}: {
  activities: RecentActivityItem[];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        <CardDescription>Latest grading and review events</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {activities.length === 0 ? (
          <p className="text-muted-foreground text-sm">No recent activity</p>
        ) : (
          activities.map((item, i) => {
            const config = activityConfig[item.type];
            if (!config) return null;

            const href = item.essay_id
              ? `/assignments/${item.assignment_id}/essays/${item.essay_id}`
              : `/assignments/${item.assignment_id}`;

            return (
              <Card size="sm" key={`${item.type}-${item.timestamp}-${i}`}>
                <CardContent>
                  <Link href={href} className="flex items-start gap-3 group">
                    <span className="mt-0.5 shrink-0">{config.icon}</span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium group-hover:underline">
                        {config.label(item)}
                      </p>
                      <p className="text-muted-foreground text-xs">
                        {item.assignment_title} &middot;{" "}
                        {formatRelativeTime(item.timestamp)}
                      </p>
                    </div>
                  </Link>
                </CardContent>
              </Card>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}
