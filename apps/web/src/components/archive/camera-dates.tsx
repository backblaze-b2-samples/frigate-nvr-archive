"use client";

import { CalendarDays } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useArchiveCameraDates } from "@/lib/queries";

export function CameraDates({ camera }: { camera: string }) {
  const { data, isLoading } = useArchiveCameraDates(camera);

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-7 w-full" />
        ))}
      </div>
    );
  }

  const dates = data ?? [];
  if (dates.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        No dated objects for this camera yet.
      </p>
    );
  }

  return (
    <ul className="space-y-1.5">
      {dates.map((d) => (
        <li
          key={d.date}
          className="flex items-center justify-between rounded px-2 py-1.5 text-xs hover:bg-muted/40"
        >
          <span className="inline-flex items-center gap-2 font-medium">
            <CalendarDays className="h-3.5 w-3.5 text-muted-foreground" />
            {d.date}
          </span>
          <span className="flex items-center gap-3 text-muted-foreground tabular-nums">
            <span>{d.objects} objects</span>
            <span className="font-medium text-foreground">{d.bytes_human}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
