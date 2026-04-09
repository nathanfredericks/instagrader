"use client";

import Link from "next/link";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AssignmentStatusBadge } from "@/components/assignment-status-badge";
import type { components } from "@/lib/api/schema";
import type { AssignmentStatus } from "@/lib/types";

type ActiveAssignment = components["schemas"]["ActiveAssignment"];

function ProgressRing({
  value,
  size = 56,
  strokeWidth = 5,
}: {
  value: number;
  size?: number;
  strokeWidth?: number;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  // strokeDashoffset sets the ring fill, rotated -90deg to start from top
  const offset = circumference - (value / 100) * circumference;

  return (
    <svg width={size} height={size} className="shrink-0 -rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className="text-muted"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="text-green-500 transition-all duration-500"
      />
    </svg>
  );
}

export function AssignmentProgressCards({
  data,
}: {
  data: ActiveAssignment[];
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Active Assignments</CardTitle>
        <Link
          href="/assignments"
          className="text-muted-foreground text-xs hover:text-foreground transition-colors"
        >
          View all assignments
        </Link>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <div className="flex h-[200px] items-center justify-center text-muted-foreground">
            No active assignments
          </div>
        ) : (
          <div className="space-y-3">
            {data.map((assignment) => {
              const pct =
                assignment.total_essays > 0
                  ? Math.round(
                      (assignment.reviewed_count / assignment.total_essays) *
                        100
                    )
                  : 0;

              return (
                <Link
                  key={assignment.id}
                  href={`/assignments/${assignment.id}`}
                  className="flex items-center gap-4 rounded-lg border p-3 transition-colors hover:bg-muted/50"
                >
                  <ProgressRing value={pct} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-sm">
                      {assignment.title}
                    </p>
                    <p className="text-muted-foreground text-xs">
                      {assignment.reviewed_count} of {assignment.total_essays}{" "}
                      reviewed
                    </p>
                  </div>
                  <AssignmentStatusBadge
                    status={assignment.status as AssignmentStatus}
                  />
                </Link>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
