"use client";

import { Boxes } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useNvrStats } from "@/lib/queries";

export function ObjectClassBreakdown() {
  const { data: stats, isLoading, error, refetch } = useNvrStats();
  const counts = stats?.label_counts ?? {};
  const entries = Object.entries(counts);
  const max = entries.reduce((m, [, n]) => Math.max(m, n), 0) || 1;

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Object Classes</CardTitle>
        <CardDescription className="text-xs">
          What Frigate detected (last 30 days)
        </CardDescription>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-6 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : entries.length === 0 ? (
          <EmptyState
            icon={Boxes}
            title="No detections yet"
            description="Archived Frigate events will break down by object class here."
          />
        ) : (
          <div className="space-y-3">
            {entries.map(([label, n]) => (
              <div key={label} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium capitalize">{label}</span>
                  <span className="text-muted-foreground tabular-nums">{n}</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${(n / max) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
