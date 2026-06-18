"use client";

import { useMemo, useState } from "react";
import { Camera, PlayCircle, Video } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { EventFiltersBar } from "./event-filters";
import { EventDetailDialog } from "./event-detail-dialog";
import { useEvents, useNvrStats } from "@/lib/queries";
import { formatDate } from "@/lib/utils";
import type { EventSearchParams, EventView } from "@frigate-nvr-archive/shared";

export function EventTimeline() {
  const [filters, setFilters] = useState<EventSearchParams>({ limit: 100 });
  const [selected, setSelected] = useState<EventView | null>(null);

  const { data: events = [], isLoading, error, refetch } = useEvents(filters);
  // Reuse the dashboard stats to populate the camera + object-class dropdowns.
  const { data: stats } = useNvrStats();

  const cameras = useMemo(
    () => (stats?.camera_summaries ?? []).map((c) => c.name),
    [stats],
  );
  const labels = useMemo(
    () => Object.keys(stats?.label_counts ?? {}),
    [stats],
  );

  return (
    <div className="space-y-6">
      <EventFiltersBar
        value={filters}
        onChange={setFilters}
        cameras={cameras}
        labels={labels}
      />

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full rounded-md" />
          ))}
        </div>
      ) : error ? (
        <Card>
          <CardContent className="p-0">
            <ErrorState error={error} onRetry={() => refetch()} />
          </CardContent>
        </Card>
      ) : events.length === 0 ? (
        <Card>
          <CardContent className="p-0">
            <EmptyState
              icon={Video}
              title="No events match"
              description="Adjust the filters, or run the archive worker to stream Frigate detection events into B2."
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {events.map((e) => (
            <button
              key={e.id}
              onClick={() => setSelected(e)}
              className="group text-left"
            >
              <Card className="card-hover overflow-hidden h-full">
                <div className="relative aspect-video bg-muted overflow-hidden">
                  {e.snapshot_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={e.snapshot_url}
                      alt={`${e.label} on ${e.camera}`}
                      className="h-full w-full object-cover transition-transform group-hover:scale-105"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center">
                      <Camera className="h-8 w-8 text-muted-foreground" />
                    </div>
                  )}
                  {e.has_clip ? (
                    <div className="absolute inset-0 flex items-center justify-center opacity-0 transition-opacity group-hover:opacity-100">
                      <PlayCircle className="h-10 w-10 text-white drop-shadow" />
                    </div>
                  ) : null}
                  <div className="absolute top-2 left-2">
                    <Badge variant="secondary" className="capitalize">
                      {e.label}
                    </Badge>
                  </div>
                </div>
                <CardContent className="p-4 space-y-1">
                  <p className="text-sm font-semibold truncate">{e.camera}</p>
                  <div className="flex items-center justify-between text-xs text-muted-foreground tabular-nums">
                    <span>{formatDate(e.start_time)}</span>
                    <span>{(e.score * 100).toFixed(0)}%</span>
                  </div>
                </CardContent>
              </Card>
            </button>
          ))}
        </div>
      )}

      <EventDetailDialog
        event={selected}
        onOpenChange={(open) => !open && setSelected(null)}
      />
    </div>
  );
}
