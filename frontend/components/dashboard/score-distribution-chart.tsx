"use client";

import { Bar, BarChart, CartesianGrid, XAxis } from "recharts";

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

type ScoreDistributionBucket =
  components["schemas"]["ScoreDistributionBucket"];

const chartConfig = {
  count: { label: "Essays", color: "var(--chart-1)" },
} satisfies ChartConfig;

export function ScoreDistributionChart({
  data,
}: {
  data: ScoreDistributionBucket[];
}) {
  const total = data.reduce((sum, b) => sum + b.count, 0);

  const chartData = data.map((bucket) => ({
    range: `${bucket.range}%`,
    count: bucket.count,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Score Distribution</CardTitle>
        <CardDescription>
          {total === 0
            ? "No graded essays yet"
            : `${total} graded essay${total !== 1 ? "s" : ""}`}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {total === 0 ? (
          <div className="flex h-[200px] items-center justify-center text-muted-foreground">
            No graded essays yet
          </div>
        ) : (
          <ChartContainer config={chartConfig} className="max-h-[250px] w-full">
            <BarChart accessibilityLayer data={chartData}>
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="range"
                tickLine={false}
                tickMargin={10}
                axisLine={false}
              />
              <ChartTooltip
                cursor={false}
                content={<ChartTooltipContent hideLabel />}
              />
              <Bar dataKey="count" fill="var(--color-count)" radius={8} />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
