"use client";

import { Label, Pie, PieChart } from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
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

type EssayStatusCounts = components["schemas"]["EssayStatusCounts"];

const chartConfig = {
  count: { label: "Essays" },
  pending: { label: "Pending", color: "var(--chart-3)" },
  processing: { label: "Processing", color: "var(--chart-4)" },
  graded: { label: "Ready for Review", color: "var(--chart-1)" },
  reviewed: { label: "Reviewed", color: "var(--chart-2)" },
  failed: { label: "Failed", color: "var(--chart-5)" },
} satisfies ChartConfig;

export function EssayStatusChart({ data }: { data: EssayStatusCounts }) {
  const total = Object.values(data).reduce((sum, n) => sum + n, 0);

  const chartData = [
    { status: "pending", count: data.pending, fill: "var(--color-pending)" },
    { status: "processing", count: data.processing, fill: "var(--color-processing)" },
    { status: "graded", count: data.graded, fill: "var(--color-graded)" },
    { status: "reviewed", count: data.reviewed, fill: "var(--color-reviewed)" },
    { status: "failed", count: data.failed, fill: "var(--color-failed)" },
  ].filter((d) => d.count > 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Essay Status</CardTitle>
        <CardDescription>
          {total === 0
            ? "No essays yet"
            : `${total} total essay${total !== 1 ? "s" : ""}`}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {total === 0 ? (
          <div className="flex h-[200px] items-center justify-center text-muted-foreground">
            No essays yet
          </div>
        ) : (
          <ChartContainer config={chartConfig} className="mx-auto aspect-square max-h-[250px]">
            <PieChart>
              <ChartTooltip
                cursor={false}
                content={<ChartTooltipContent hideLabel />}
              />
              <Pie
                data={chartData}
                dataKey="count"
                nameKey="status"
                innerRadius={60}
                strokeWidth={5}
              >
                <Label
                  content={({ viewBox }) => {
                    if (viewBox && "cx" in viewBox && "cy" in viewBox) {
                      return (
                        <text
                          x={viewBox.cx}
                          y={viewBox.cy}
                          textAnchor="middle"
                          dominantBaseline="middle"
                        >
                          <tspan
                            x={viewBox.cx}
                            y={viewBox.cy}
                            className="fill-foreground text-3xl font-bold"
                          >
                            {total}
                          </tspan>
                          <tspan
                            x={viewBox.cx}
                            y={(viewBox.cy || 0) + 24}
                            className="fill-muted-foreground"
                          >
                            essays
                          </tspan>
                        </text>
                      );
                    }
                  }}
                />
              </Pie>
            </PieChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
