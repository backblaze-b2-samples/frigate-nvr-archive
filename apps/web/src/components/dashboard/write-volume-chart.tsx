"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";
import {
  Card,
  CardAction,
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
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useWriteVolume } from "@/lib/queries";

const chartConfig = {
  mb: {
    label: "MB written",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig;

export function WriteVolumeChart() {
  const { data: volume, error, refetch } = useWriteVolume(7);

  // Chart in MB so day-to-day write rate is legible; the headline below shows
  // the human-readable total across the window.
  const data = useMemo(
    () =>
      (volume ?? []).map((d) => ({
        date: new Date(d.date + "T00:00:00").toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        }),
        mb: Math.round((d.bytes_written / (1024 * 1024)) * 10) / 10,
      })),
    [volume],
  );

  const totalBytes = (volume ?? []).reduce((s, d) => s + d.bytes_written, 0);
  const totalHuman =
    totalBytes >= 1024 * 1024 * 1024
      ? `${(totalBytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
      : `${(totalBytes / (1024 * 1024)).toFixed(1)} MB`;

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Write Rate to B2</CardTitle>
        <CardDescription className="text-xs">
          Footage archived per day, last 7 days
        </CardDescription>
        <CardAction className="text-right self-center">
          <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
            Total
          </div>
          <div className="text-lg font-semibold tabular-nums tracking-tight leading-tight">
            {totalHuman}
          </div>
        </CardAction>
      </CardHeader>
      <CardContent className="p-5">
        {error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="No footage archived yet"
            description="Run the archive worker to stream Frigate events into B2 and see the daily write rate here."
          />
        ) : (
          <ChartContainer config={chartConfig} className="h-[240px] w-full">
            <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="write-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-mb)" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="var(--color-mb)" stopOpacity={0.55} />
                </linearGradient>
              </defs>
              <CartesianGrid
                vertical={false}
                strokeDasharray="3 3"
                stroke="var(--border)"
              />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tickMargin={10}
                fontSize={11}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tickMargin={6}
                fontSize={11}
                width={34}
              />
              <ChartTooltip
                cursor={{ fill: "var(--accent-subtle)" }}
                content={<ChartTooltipContent />}
              />
              <Bar
                dataKey="mb"
                fill="url(#write-fill)"
                radius={[4, 4, 0, 0]}
                animationDuration={500}
                animationEasing="ease-out"
              />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
