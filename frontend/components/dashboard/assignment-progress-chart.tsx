"use client";

import { Bar, BarChart, XAxis, YAxis } from "recharts";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import type { components } from "@/lib/api/schema";

type AssignmentStatusCounts = components["schemas"]["AssignmentStatusCounts"];

const chartConfig = {
  count: { label: "Assignments" },
  draft: { label: "Draft", color: "var(--color-muted-foreground)" },
  grading: { label: "Grading", color: "var(--color-blue-500)" },
  review: { label: "Review", color: "var(--color-amber-500)" },
  completed: { label: "Completed", color: "var(--color-green-500)" },
} satisfies ChartConfig;

export function AssignmentProgressChart({
  data,
}: {
  data: AssignmentStatusCounts;
}) {
  const total = Object.values(data).reduce((sum, n) => sum + n, 0);

  const chartData = [
    { status: "Draft", count: data.draft, fill: "var(--color-draft)" },
    { status: "Grading", count: data.grading, fill: "var(--color-grading)" },
    { status: "Review", count: data.review, fill: "var(--color-review)" },
    { status: "Completed", count: data.completed, fill: "var(--color-completed)" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Assignment Progress</CardTitle>
      </CardHeader>
      <CardContent>
        {total === 0 ? (
          <div className="flex h-[200px] items-center justify-center text-muted-foreground">
            No assignments yet
          </div>
        ) : (
          <ChartContainer config={chartConfig} className="max-h-[250px] w-full">
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ left: 0 }}
            >
              <YAxis
                dataKey="status"
                type="category"
                tickLine={false}
                axisLine={false}
                width={80}
              />
              <XAxis type="number" hide />
              <ChartTooltip
                cursor={false}
                content={<ChartTooltipContent hideLabel />}
              />
              <Bar dataKey="count" radius={5} />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
